# include <sys/prctl.h>
# include <pthread.h>
# include <unistd.h>

static void * thread_main() {
	char * name = "thread-2";
	prctl(PR_SET_NAME, (unsigned long)name);
	sleep(1);
}

int main() {
	char * name = "thread-1";
	prctl(PR_SET_NAME, (unsigned long)name);

	pthread_t thrd;
	pthread_create(&thrd, NULL, thread_main, NULL);
	pthread_join(thrd, NULL);
	return 0;
}
