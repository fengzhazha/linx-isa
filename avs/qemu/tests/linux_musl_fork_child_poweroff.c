#include <fcntl.h>
#include <signal.h>
#include <stdlib.h>
#include <sys/reboot.h>
#include <sys/syscall.h>
#include <unistd.h>

static void emit_marker(const char *s)
{
	size_t len = 0;

	while (s[len])
		len++;
	(void)syscall(SYS_write, STDOUT_FILENO, s, len);
	(void)syscall(SYS_write, STDOUT_FILENO, "\n", 1);
}

static pid_t raw_fork(void)
{
#ifdef SYS_fork
	return (pid_t)syscall(SYS_fork);
#else
	return (pid_t)syscall(SYS_clone, (long)SIGCHLD, 0L, 0L, 0L, 0L);
#endif
}

static void poweroff_now(void)
{
	sync();
	reboot(RB_POWER_OFF);
}

int main(void)
{
	int cfd = open("/dev/console", O_RDWR);
	pid_t pid;

	if (cfd < 0)
		cfd = open("/dev/ttyS0", O_RDWR);
	if (cfd >= 0) {
		(void)dup2(cfd, STDIN_FILENO);
		(void)dup2(cfd, STDOUT_FILENO);
		(void)dup2(cfd, STDERR_FILENO);
		if (cfd > STDERR_FILENO)
			(void)close(cfd);
	}

	emit_marker("MUSL_FORK_CHILD_POWEROFF_START");
	pid = raw_fork();
	if (pid < 0) {
		emit_marker("MUSL_FORK_CHILD_POWEROFF_FORK_FAIL");
		poweroff_now();
		return 1;
	}

	if (pid == 0) {
		emit_marker("MUSL_FORK_CHILD_POWEROFF_PASS");
		poweroff_now();
		return 0;
	}

	emit_marker("MUSL_FORK_CHILD_POWEROFF_PARENT");
	for (;;)
		pause();
}
