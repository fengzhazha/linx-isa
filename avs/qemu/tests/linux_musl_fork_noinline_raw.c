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

__attribute__((noinline, returns_twice)) static pid_t spawn_child_process(void)
{
#ifdef SYS_fork
	return (pid_t)syscall(SYS_fork);
#endif
	return (pid_t)syscall(SYS_clone, (long)SIGCHLD, 0L, 0L, 0L, 0L);
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
	char buf[192];

	if (cfd < 0)
		cfd = open("/dev/ttyS0", O_RDWR);
	if (cfd >= 0) {
		(void)dup2(cfd, STDIN_FILENO);
		(void)dup2(cfd, STDOUT_FILENO);
		(void)dup2(cfd, STDERR_FILENO);
		if (cfd > STDERR_FILENO)
			(void)close(cfd);
	}

	emit_marker("MUSL_FORK_NOINLINE_RAW_START");
	pid = spawn_child_process();
	snprintf(buf, sizeof(buf), "MUSL_FORK_NOINLINE_RAW_ROLE pid=%ld self=%ld ppid=%ld",
		 (long)pid, (long)getpid(), (long)getppid());
	emit_marker(buf);

	if (pid < 0) {
		emit_marker("MUSL_FORK_NOINLINE_RAW_FORK_FAIL");
		poweroff_now();
		return 1;
	}

	if (pid == 0) {
		emit_marker("MUSL_FORK_NOINLINE_RAW_CHILD");
		(void)syscall(SYS_exit, 37);
		emit_marker("MUSL_FORK_NOINLINE_RAW_RETURNED");
		poweroff_now();
		return 3;
	}

	emit_marker("MUSL_FORK_NOINLINE_RAW_PARENT");
	waited = waitpid(pid, &status, 0);
	if (waited != pid || !WIFEXITED(status) || WEXITSTATUS(status) != 37) {
		snprintf(buf, sizeof(buf),
			 "MUSL_FORK_NOINLINE_RAW_FAIL pid=%ld waited=%ld status=%d errno=%d",
			 (long)pid, (long)waited, status, errno);
		emit_marker(buf);
		poweroff_now();
		return 2;
	}

	emit_marker("MUSL_FORK_NOINLINE_RAW_PASS");
	poweroff_now();
	return 0;
}
