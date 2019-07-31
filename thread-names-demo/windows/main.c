# include <windows.h>
# include <processthreadsapi.h>

DWORD WINAPI thread_main( LPVOID lpParam ) {
	SetThreadDescription(GetCurrentThread(), L"thread-2");
        Sleep(1000);
	return 0;
}

int main() {
	SetThreadDescription(GetCurrentThread(), L"thread-1");

	DWORD tid;
	HANDLE h = CreateThread(NULL, 0, thread_main, NULL, 0, &tid);
        WaitForSingleObject(h, INFINITE);
	Sleep(1000);

        return 0;
}
