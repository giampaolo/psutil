/*
 * $Id$
 *
 * Security related functions for Windows platform (Set privileges such as 
 * SeDebug), as well as security helper functions.
 */

#include <windows.h>


BOOL SetPrivilege(HANDLE hToken, LPCTSTR Privilege, BOOL bEnablePrivilege)
{
    TOKEN_PRIVILEGES tp;
    LUID luid;
    TOKEN_PRIVILEGES tpPrevious;
    DWORD cbPrevious=sizeof(TOKEN_PRIVILEGES);

    if(!LookupPrivilegeValue( NULL, Privilege, &luid )) return FALSE;

    //
    // first pass.  get current privilege setting
    //
    tp.PrivilegeCount = 1;
    tp.Privileges[0].Luid = luid;
    tp.Privileges[0].Attributes = 0;

    AdjustTokenPrivileges(
        hToken,
        FALSE,
        &tp,
        sizeof(TOKEN_PRIVILEGES),
        &tpPrevious,
        &cbPrevious
    );

    if (GetLastError() != ERROR_SUCCESS) return FALSE;

    // 
    // second pass. set privilege based on previous setting
    //
    tpPrevious.PrivilegeCount = 1;
    tpPrevious.Privileges[0].Luid = luid;

    if(bEnablePrivilege) {
        tpPrevious.Privileges[0].Attributes |= (SE_PRIVILEGE_ENABLED);
    }
    
    else {
        tpPrevious.Privileges[0].Attributes ^= (SE_PRIVILEGE_ENABLED &
                tpPrevious.Privileges[0].Attributes);
    }

    AdjustTokenPrivileges(
        hToken,
        FALSE,
        &tpPrevious,
        cbPrevious,
        NULL,
        NULL
    );

    if (GetLastError() != ERROR_SUCCESS) return FALSE;

    return TRUE;
}


int SetSeDebug() 
{ 
    HANDLE hToken;
    if(!OpenThreadToken(GetCurrentThread(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, FALSE, &hToken)){
        if (GetLastError() == ERROR_NO_TOKEN){
            if (!ImpersonateSelf(SecurityImpersonation)){
                //Log2File("Error setting impersonation [SetSeDebug()]", L_DEBUG);
                return 0;
            }
            if(!OpenThreadToken(GetCurrentThread(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, FALSE, &hToken)){
                //Log2File("Error Opening Thread Token", L_DEBUG);
                return 0;
            }
        }
    }

    // enable SeDebugPrivilege (open any process)
    if(!SetPrivilege(hToken, SE_DEBUG_NAME, TRUE)){
        //Log2File("Error setting SeDebug Privilege [SetPrivilege()]", L_WARN);
        return 0;
    }

    CloseHandle(hToken);
    return 1;
}


int UnsetSeDebug()
{
    HANDLE hToken;
    if(!OpenThreadToken(GetCurrentThread(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, FALSE, &hToken)){
        if(GetLastError() == ERROR_NO_TOKEN){
            if(!ImpersonateSelf(SecurityImpersonation)){
                //Log2File("Error setting impersonation! [UnsetSeDebug()]", L_DEBUG);
                return 0;
            }

            if(!OpenThreadToken(GetCurrentThread(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, FALSE, &hToken)){
                //Log2File("Error Opening Thread Token! [UnsetSeDebug()]", L_DEBUG);
                return 0;
            }
        }
    }

    //now disable SeDebug
    if(!SetPrivilege(hToken, SE_DEBUG_NAME, FALSE)){
        //Log2File("Error unsetting SeDebug Privilege [SetPrivilege()]", L_WARN);
        return 0;
    }

    CloseHandle(hToken);
    return 1;
}

