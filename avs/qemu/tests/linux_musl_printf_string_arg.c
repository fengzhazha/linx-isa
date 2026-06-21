#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/reboot.h>
#include <unistd.h>

static size_t raw_len(const char *s)
{
	size_t n = 0;
	while (s[n])
		n++;
	return n;
}

static void raw_marker(const char *s)
{
	(void)write(STDOUT_FILENO, s, raw_len(s));
	(void)write(STDOUT_FILENO, "\n", 1);
}

static void poweroff(int code)
{
	sync();
	reboot(RB_POWER_OFF);
	(void)code;
}

int main(void)
{
	static const char value[] = "MUSL_PRINTF_STRING_ARG_VALUE";
	char buf[64];
	int cfd;
	int n;

	cfd = open("/dev/console", O_RDWR);
	if (cfd < 0)
		cfd = open("/dev/ttyS0", O_RDWR);
	if (cfd >= 0) {
		(void)dup2(cfd, STDIN_FILENO);
		(void)dup2(cfd, STDOUT_FILENO);
		(void)dup2(cfd, STDERR_FILENO);
		if (cfd > STDERR_FILENO)
			(void)close(cfd);
	}

	raw_marker("MUSL_PRINTF_STRING_ARG_START");

	n = snprintf(buf, sizeof buf, "%s", value);
	if (n != (int)raw_len(value) || memcmp(buf, value, raw_len(value) + 1) != 0) {
		raw_marker("MUSL_PRINTF_STRING_ARG_FAIL_SNPRINTF");
		raw_marker(buf);
		poweroff(2);
		return 2;
	}

	printf("MUSL_PRINTF_STRING_ARG_PRINTF %s\n", value);
	fflush(stdout);

	raw_marker("MUSL_PRINTF_STRING_ARG_PASS");
	poweroff(0);
	return 0;
}
