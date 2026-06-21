#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/reboot.h>
#include <sys/syscall.h>
#include <sys/wait.h>
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
	int status = 0x13579bdf;
	pid_t pid;
	pid_t waited;

	if (cfd < 0)
		cfd = open("/dev/ttyS0", O_RDWR);
	if (cfd >= 0) {
		(void)dup2(cfd, STDIN_FILENO);
		(void)dup2(cfd, STDOUT_FILENO);
		(void)dup2(cfd, STDERR_FILENO);
		if (cfd > STDERR_FILENO)
			(void)close(cfd);
	}

	emit_marker("MUSL_FORK_WAIT_START");
	pid = raw_fork();
	if (pid < 0) {
		emit_marker("MUSL_FORK_WAIT_FORK_FAIL");
		poweroff_now();
		return 1;
	}

	if (pid == 0) {
		emit_marker("MUSL_FORK_WAIT_CHILD");
		_exit(37);
	}

	emit_marker("MUSL_FORK_WAIT_PARENT");
	waited = waitpid(pid, &status, 0);
	if (waited != pid || !WIFEXITED(status) || WEXITSTATUS(status) != 37) {
		char buf[160];
		int n = snprintf(buf, sizeof(buf),
				 "MUSL_FORK_WAIT_FAIL pid=%ld waited=%ld status=%d errno=%d",
				 (long)pid, (long)waited, status, errno);
		if (n > 0)
			emit_marker(buf);
		poweroff_now();
		return 2;
	}

	emit_marker("MUSL_FORK_WAIT_PASS");
	poweroff_now();
	return 0;
}
