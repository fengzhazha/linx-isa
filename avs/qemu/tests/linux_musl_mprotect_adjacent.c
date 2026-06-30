#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/reboot.h>
#include <unistd.h>

static void emit(const char *s)
{
	size_t n = 0;

	while (s[n])
		n++;
	(void)write(STDOUT_FILENO, s, n);
}

static void emit_line(const char *s)
{
	emit(s);
	emit("\n");
}

static void emit_hex(uintptr_t value)
{
	static const char hex[] = "0123456789abcdef";
	char buf[2 + sizeof(uintptr_t) * 2];
	size_t i;

	buf[0] = '0';
	buf[1] = 'x';
	for (i = 0; i < sizeof(uintptr_t) * 2; i++) {
		unsigned int shift = (unsigned int)((sizeof(uintptr_t) * 2 - 1 - i) * 4);

		buf[2 + i] = hex[(value >> shift) & 0xfu];
	}
	(void)write(STDOUT_FILENO, buf, sizeof(buf));
}

static void emit_u32(unsigned int value)
{
	char buf[10];
	size_t pos = sizeof(buf);

	if (value == 0) {
		emit("0");
		return;
	}
	while (value != 0 && pos != 0) {
		buf[--pos] = (char)('0' + (value % 10));
		value /= 10;
	}
	(void)write(STDOUT_FILENO, buf + pos, sizeof(buf) - pos);
}

static void poweroff(void)
{
	sync();
	reboot(RB_POWER_OFF);
}

static void setup_console(void)
{
	int fd = open("/dev/console", O_RDWR);

	if (fd < 0)
		fd = open("/dev/ttyS0", O_RDWR);
	if (fd >= 0) {
		(void)dup2(fd, STDIN_FILENO);
		(void)dup2(fd, STDOUT_FILENO);
		(void)dup2(fd, STDERR_FILENO);
		if (fd > STDERR_FILENO)
			(void)close(fd);
	}
}

static int fail_errno(const char *stage, void *base)
{
	emit("MUSL_MPROTECT_ADJACENT_FAIL: ");
	emit(stage);
	emit(" base=");
	emit_hex((uintptr_t)base);
	emit(" errno=");
	emit_u32((unsigned int)errno);
	emit("\n");
	poweroff();
	return 2;
}

int main(void)
{
	const size_t page = 0x1000;
	volatile unsigned char *q;
	void *base;

	setup_console();
	emit_line("MUSL_MPROTECT_ADJACENT_START");

	base = mmap(NULL, page * 2, PROT_READ | PROT_WRITE,
		    MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (base == MAP_FAILED)
		return fail_errno("mmap", base);

	emit("MUSL_MPROTECT_ADJACENT_BASE base=");
	emit_hex((uintptr_t)base);
	emit(" second=");
	emit_hex((uintptr_t)base + page);
	emit("\n");

	q = (volatile unsigned char *)base;
	q[0] = 0x11;
	q[page + 0x10] = 0x22;

	errno = 0;
	if (mprotect(base, page, PROT_READ) != 0)
		return fail_errno("mprotect-read", base);

	if (q[page + 0x10] != 0x22) {
		emit_line("MUSL_MPROTECT_ADJACENT_FAIL: pre-merge adjacent mismatch");
		poweroff();
		return 3;
	}

	errno = 0;
	if (mprotect(base, page, PROT_READ | PROT_WRITE) != 0)
		return fail_errno("mprotect-rw", base);

	q[page + 0x10] = 0x33;
	if (q[page + 0x10] != 0x33) {
		emit_line("MUSL_MPROTECT_ADJACENT_FAIL: post-merge adjacent mismatch");
		poweroff();
		return 4;
	}

	if (munmap(base, page * 2) != 0)
		return fail_errno("munmap", base);

	emit_line("MUSL_MPROTECT_ADJACENT_PASS");
	poweroff();
	return 0;
}
