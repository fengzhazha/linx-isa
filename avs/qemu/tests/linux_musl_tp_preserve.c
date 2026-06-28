#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/reboot.h>
#include <sys/time.h>
#include <unistd.h>

static int log_fd = STDERR_FILENO;

static uintptr_t read_tp(void)
{
	uintptr_t tp;

	__asm__ volatile("ssrget %1, ->%0"
			 : "=r"(tp)
			 : "i"(0)
			 : "memory");
	return tp;
}

static size_t raw_len(const char *s)
{
	size_t n = 0;

	while (s[n])
		n++;
	return n;
}

static void emit_marker(const char *s)
{
	(void)write(log_fd, s, raw_len(s));
	(void)write(log_fd, "\n", 1);
}

static void emit_hex(uintptr_t v)
{
	static const char hex[] = "0123456789abcdef";
	char buf[2 + sizeof(uintptr_t) * 2 + 1];
	size_t i;

	buf[0] = '0';
	buf[1] = 'x';
	for (i = 0; i < sizeof(uintptr_t) * 2; i++) {
		unsigned shift = (unsigned)((sizeof(uintptr_t) * 2 - 1 - i) * 4);
		buf[2 + i] = hex[(v >> shift) & 0xfu];
	}
	buf[2 + sizeof(uintptr_t) * 2] = '\n';
	(void)write(log_fd, buf, sizeof(buf));
}

static void poweroff(int code)
{
	sync();
	reboot(RB_POWER_OFF);
	(void)code;
}

static int check_tp(const char *label, uintptr_t expected)
{
	uintptr_t tp = read_tp();

	if (!tp || tp != expected) {
		emit_marker(label);
		emit_hex(tp);
		emit_hex(expected);
		poweroff(2);
		return -1;
	}
	return 0;
}

int main(void)
{
	uintptr_t initial_tp;
	int i;

	log_fd = open("/dev/console", O_WRONLY);
	if (log_fd < 0)
		log_fd = open("/dev/ttyS0", O_WRONLY);
	if (log_fd < 0)
		log_fd = STDERR_FILENO;

	emit_marker("MUSL_TP_PRESERVE_START");

	initial_tp = read_tp();
	if (!initial_tp) {
		emit_marker("MUSL_TP_PRESERVE_FAIL_ZERO_INITIAL");
		poweroff(2);
		return 2;
	}

	for (i = 0; i < 64; i++) {
		struct timeval tv;
		char *p;
		size_t mb_cur_max;

		if (gettimeofday(&tv, 0) != 0) {
			emit_marker("MUSL_TP_PRESERVE_FAIL_GETTIMEOFDAY");
			poweroff(3);
			return 3;
		}
		if (check_tp("MUSL_TP_PRESERVE_FAIL_AFTER_TIME", initial_tp) < 0)
			return 4;

		p = malloc((size_t)i + 32);
		if (!p) {
			emit_marker("MUSL_TP_PRESERVE_FAIL_MALLOC");
			poweroff(5);
			return 5;
		}
		memset(p, i, (size_t)i + 32);
		free(p);
		if (check_tp("MUSL_TP_PRESERVE_FAIL_AFTER_MALLOC", initial_tp) < 0)
			return 6;

		mb_cur_max = MB_CUR_MAX;
		if (mb_cur_max < 1) {
			emit_marker("MUSL_TP_PRESERVE_FAIL_MB_CUR_MAX");
			poweroff(7);
			return 7;
		}
		if (check_tp("MUSL_TP_PRESERVE_FAIL_AFTER_MB_CUR_MAX", initial_tp) < 0)
			return 8;
	}

	emit_marker("MUSL_TP_PRESERVE_PASS");
	poweroff(0);
	return 0;
}
