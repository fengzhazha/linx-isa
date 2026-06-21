#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/reboot.h>
#include <unistd.h>

static int log_fd = STDERR_FILENO;

static size_t raw_len(const char *s)
{
	size_t n = 0;
	while (s[n])
		n++;
	return n;
}

static void log_marker(const char *s)
{
	(void)write(log_fd, s, raw_len(s));
	(void)write(log_fd, "\n", 1);
}

static void log_i64(long v)
{
	char buf[32];
	unsigned long x;
	size_t n = 0;

	if (v < 0) {
		(void)write(log_fd, "-", 1);
		x = (unsigned long)(-v);
	} else {
		x = (unsigned long)v;
	}
	do {
		buf[n++] = (char)('0' + (x % 10));
		x /= 10;
	} while (x);
	while (n)
		(void)write(log_fd, &buf[--n], 1);
}

static void log_fd_errno(const char *prefix, int fd, int err)
{
	(void)write(log_fd, prefix, raw_len(prefix));
	(void)write(log_fd, " fd=", 4);
	log_i64(fd);
	(void)write(log_fd, " errno=", 7);
	log_i64(err);
	(void)write(log_fd, "\n", 1);
}

static void poweroff(int code)
{
	sync();
	reboot(RB_POWER_OFF);
	(void)code;
}

int main(void)
{
	static const char expected[] = "MUSL_FILE_STDIO_LINE 0.819302\n";
	char buf[128];
	int fd;
	ssize_t rd;

	log_fd = open("/dev/console", O_WRONLY);
	if (log_fd < 0)
		log_fd = open("/dev/ttyS0", O_WRONLY);
	if (log_fd < 0)
		log_fd = STDERR_FILENO;

	log_marker("MUSL_FILE_STDIO_START");

	fd = open("file_stdio.out", O_RDWR | O_CREAT | O_TRUNC, 0644);
	if (fd < 0) {
		log_marker("MUSL_FILE_STDIO_FAIL_OPEN");
		poweroff(2);
		return 2;
	}

	if (fd != STDOUT_FILENO && dup2(fd, STDOUT_FILENO) < 0) {
		log_fd_errno("MUSL_FILE_STDIO_FAIL_DUP2", fd, errno);
		log_marker("MUSL_FILE_STDIO_FAIL_DUP2");
		poweroff(3);
		return 3;
	}
	log_fd_errno("MUSL_FILE_STDIO_FD", fd, 0);

	log_marker("MUSL_FILE_STDIO_BEFORE_PRINTF");
	printf("MUSL_FILE_STDIO_LINE %.6f\n", 0.819302);
	log_marker("MUSL_FILE_STDIO_BEFORE_FFLUSH");
	if (fflush(stdout) != 0) {
		log_marker("MUSL_FILE_STDIO_FAIL_FFLUSH");
		poweroff(4);
		return 4;
	}
	log_marker("MUSL_FILE_STDIO_AFTER_FFLUSH");

	if (lseek(fd, 0, SEEK_SET) < 0) {
		log_marker("MUSL_FILE_STDIO_FAIL_LSEEK");
		poweroff(5);
		return 5;
	}

	memset(buf, 0, sizeof buf);
	rd = read(fd, buf, sizeof buf - 1);
	if (rd < 0) {
		log_marker("MUSL_FILE_STDIO_FAIL_READ");
		poweroff(6);
		return 6;
	}
	if ((size_t)rd != raw_len(expected) || memcmp(buf, expected, raw_len(expected)) != 0) {
		log_marker("MUSL_FILE_STDIO_FAIL_CONTENT");
		log_marker(buf);
		poweroff(7);
		return 7;
	}

	log_marker("MUSL_FILE_STDIO_PASS");
	poweroff(0);
	return 0;
}
