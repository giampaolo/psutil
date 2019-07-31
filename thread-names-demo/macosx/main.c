# include <pthread.h>
# include <unistd.h>

static void * thread_main() {
        pthread_setname_np(pthread_self(), "thread-2");
        sleep(1);
}

int main() {
        pthread_setname_np(pthread_self(), "thread-1");

        pthread_t thrd;
        pthread_create(&thrd, NULL, thread_main, NULL);
        pthread_join(thrd, NULL);
        return 0;
}
