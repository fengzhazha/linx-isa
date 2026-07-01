#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <sys/reboot.h>
#include <sys/time.h>
#include <time.h>
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
		x = -(unsigned long)v;
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

static void log_errno(const char *prefix, int err)
{
	(void)write(log_fd, prefix, raw_len(prefix));
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
	struct timespec ts;
	struct timeval tv;

	log_fd = open("/dev/console", O_WRONLY);
	if (log_fd < 0)
		log_fd = open("/dev/ttyS0", O_WRONLY);
	if (log_fd < 0)
		log_fd = STDERR_FILENO;

	log_marker("MUSL_TIME_SYSCALLS_START");

	errno = 0;
	if (clock_gettime(CLOCK_REALTIME, &ts) != 0) {
		log_errno("MUSL_TIME_SYSCALLS_FAIL_CLOCK_GETTIME", errno);
		poweroff(2);
		return 2;
	}
	if (ts.tv_nsec < 0 || ts.tv_nsec >= 1000000000L) {
		log_marker("MUSL_TIME_SYSCALLS_FAIL_CLOCK_RANGE");
		poweroff(3);
		return 3;
	}

	errno = 0;
	if (gettimeofday(&tv, 0) != 0) {
		log_errno("MUSL_TIME_SYSCALLS_FAIL_GETTIMEOFDAY", errno);
		poweroff(4);
		return 4;
	}
	if (tv.tv_usec < 0 || tv.tv_usec >= 1000000L) {
		log_marker("MUSL_TIME_SYSCALLS_FAIL_TIMEVAL_RANGE");
		poweroff(5);
		return 5;
	}

	log_marker("MUSL_TIME_SYSCALLS_PASS");
	poweroff(0);
	return 0;
}
