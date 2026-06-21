#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
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

static void setup_console(void)
{
	int cfd = open("/dev/console", O_RDWR);

	if (cfd < 0)
		cfd = open("/dev/ttyS0", O_RDWR);
	if (cfd >= 0) {
		if (cfd != STDIN_FILENO)
			(void)dup2(cfd, STDIN_FILENO);
		if (cfd != STDOUT_FILENO)
			(void)dup2(cfd, STDOUT_FILENO);
		if (cfd != STDERR_FILENO)
			(void)dup2(cfd, STDERR_FILENO);
		if (cfd > STDERR_FILENO)
			(void)close(cfd);
	}
}

static void poweroff_now(void)
{
	sync();
	reboot(RB_POWER_OFF);
}

int main(int argc, char **argv)
{
	int status = 0x13579bdf;
	pid_t pid;
	pid_t waited;

	setup_console();

	if (argc > 1 && strcmp(argv[1], "child") == 0) {
		emit_marker("MUSL_FORK_EXEC_PATH_CHILD_ENTRY");
		void *p = malloc(128);
		if (!p) {
			emit_marker("MUSL_FORK_EXEC_PATH_CHILD_MALLOC_FAIL");
			_exit(125);
		}
		emit_marker("MUSL_FORK_EXEC_PATH_CHILD_BEFORE_PRINTF");
		printf("MUSL_FORK_EXEC_PATH_PRINTF %-13f\n", 0.819302);
		fflush(stdout);
		free(p);
		emit_marker("MUSL_FORK_EXEC_PATH_CHILD");
		_exit(37);
	}

	emit_marker("MUSL_FORK_EXEC_PATH_START");
	pid = raw_fork();
	if (pid < 0) {
		emit_marker("MUSL_FORK_EXEC_PATH_FORK_FAIL");
		poweroff_now();
		return 1;
	}

	if (pid == 0) {
		char *child_argv[] = { "/child_exec_path", "child", NULL };
		char *child_envp[] = { NULL };

		emit_marker("MUSL_FORK_EXEC_PATH_BEFORE_EXEC");
		{
			int rc = execve(child_argv[0], child_argv, child_envp);
			int saved_errno = errno;
			char buf[128];
			int n = snprintf(buf, sizeof(buf),
					 "MUSL_FORK_EXEC_PATH_EXEC_FAIL rc=%d errno=%d",
					 rc, saved_errno);
			if (n > 0)
				emit_marker(buf);
		}
		_exit(124);
	}

	emit_marker("MUSL_FORK_EXEC_PATH_PARENT");
	waited = waitpid(pid, &status, 0);
	if (waited != pid || !WIFEXITED(status) || WEXITSTATUS(status) != 37) {
		char buf[192];
		int n = snprintf(buf, sizeof(buf),
				 "MUSL_FORK_EXEC_PATH_FAIL pid=%ld waited=%ld status=%d errno=%d",
				 (long)pid, (long)waited, status, errno);
		if (n > 0)
			emit_marker(buf);
		poweroff_now();
		return 2;
	}

	emit_marker("MUSL_FORK_EXEC_PATH_PASS");
	poweroff_now();
	return 0;
}
