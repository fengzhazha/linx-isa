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

int main(void)
{
	const size_t old_len = 0x21000;
	const size_t new_len = 0x41000;
	volatile unsigned char *q;
	void *p;
	void *moved;

	setup_console();
	emit_line("MUSL_MREMAP_END_START");

	p = mmap(NULL, old_len, PROT_READ | PROT_WRITE,
		 MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (p == MAP_FAILED) {
		emit("MUSL_MREMAP_END_FAIL: mmap errno=");
		emit_u32((unsigned int)errno);
		emit("\n");
		poweroff();
		return 2;
	}

	q = (volatile unsigned char *)p;
	q[0] = 0x11;
	q[old_len - 1] = 0x22;

	errno = 0;
	moved = mremap(p, old_len, new_len, MREMAP_MAYMOVE);
	if (moved == MAP_FAILED) {
		emit("MUSL_MREMAP_END_FAIL: mremap errno=");
		emit_u32((unsigned int)errno);
		emit("\n");
		(void)munmap(p, old_len);
		poweroff();
		return 3;
	}

	emit("MUSL_MREMAP_END_BASE old=");
	emit_hex((uintptr_t)p);
	emit(" new=");
	emit_hex((uintptr_t)moved);
	emit(" end=");
	emit_hex((uintptr_t)moved + new_len - 1);
	emit("\n");

	q = (volatile unsigned char *)moved;
	q[0] ^= 0x01;
	q[old_len - 1] ^= 0x02;
	q[new_len - 1] = 0x33;

	if (q[new_len - 1] != 0x33) {
		emit_line("MUSL_MREMAP_END_FAIL: end byte mismatch");
		(void)munmap(moved, new_len);
		poweroff();
		return 4;
	}

	(void)munmap(moved, new_len);
	emit_line("MUSL_MREMAP_END_PASS");
	poweroff();
	return 0;
}
