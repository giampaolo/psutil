/*
 * $Id$
 *
 * Security related functions for Windows platform (Set privileges such as
 * SeDebug), as well as security helper functions.
 */

#include <windows.h>


BOOL SetPrivilege(HANDLE hToken, LPCTSTR Privilege, BOOL bEnablePrivilege);
int SetSeDebug();
int UnsetSeDebug();

