/*
 * Copyright (c) 2017, Arnon Yaari
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/* The kernel is always 64 bit but Python is usually compiled as a 32 bit
 * process. We're reading the kernel memory to get the network connections,
 * so we need the structs we read to be defined with 64 bit "pointers".
 * Here are the partial definitions of the structs we use, taken from the
 * header files, with data type sizes converted to their 64 bit counterparts,
 * and unused data truncated. */

#ifdef __64BIT__
/* In case we're in a 64 bit process after all */
#include <sys/socketvar.h>
#include <sys/protosw.h>
#include <sys/unpcb.h>
#include <sys/mbuf_base.h>
#include <sys/mbuf_macro.h>
#include <netinet/ip_var.h>
#include <netinet/tcp.h>
#include <netinet/tcpip.h>
#include <netinet/tcp_timer.h>
#include <netinet/tcp_var.h>
#define file64 file
#define socket64 socket
#define protosw64 protosw
#define inpcb64 inpcb
#define tcpcb64 tcpcb
#define unpcb64 unpcb
#define mbuf64 mbuf
#else       /* __64BIT__ */
  struct file64 {
    int f_flag;
    int f_count;
    int f_options;
    int f_type;
    u_longlong_t f_data;
 };

 struct socket64 {
    short   so_type;                 /* generic type, see socket.h */
    short   so_options;              /* from socket call, see socket.h */
    ushort  so_linger;               /* time to linger while closing */
    short   so_state;                /* internal state flags SS_*, below */
    u_longlong_t so_pcb;             /* protocol control block */
    u_longlong_t so_proto;           /* protocol handle */
 };

 struct protosw64 {
    short   pr_type;                 /* socket type used for */
    u_longlong_t pr_domain;          /* domain protocol a member of */
    short   pr_protocol;             /* protocol number */
    short   pr_flags;                /* see below */
 };

 struct inpcb64 {
    u_longlong_t inp_next,inp_prev;
                                     /* pointers to other pcb's */
    u_longlong_t inp_head;           /* pointer back to chain of inpcb's
                                       for this protocol */
    u_int32_t inp_iflowinfo;         /* input flow label */
    u_short inp_fport;               /* foreign port */
    u_int16_t inp_fatype;            /* foreign address type */
    union   in_addr_6 inp_faddr_6;   /* foreign host table entry */
    u_int32_t inp_oflowinfo;         /* output flow label */
    u_short inp_lport;               /* local port */
    u_int16_t inp_latype;            /* local address type */
    union   in_addr_6 inp_laddr_6;   /* local host table entry */
    u_longlong_t inp_socket;         /* back pointer to socket */
    u_longlong_t inp_ppcb;           /* pointer to per-protocol pcb */
    u_longlong_t space_rt;
    struct  sockaddr_in6 spare_dst;
    u_longlong_t inp_ifa;            /* interface address to use */
    int     inp_flags;               /* generic IP/datagram flags */
};

struct tcpcb64 {
    u_longlong_t seg__next;
    u_longlong_t seg__prev;
    short   t_state;                 /* state of this connection */
};

struct unpcb64 {
        u_longlong_t unp_socket;     /* pointer back to socket */
        u_longlong_t unp_vnode;      /* if associated with file */
        ino_t   unp_vno;             /* fake vnode number */
        u_longlong_t unp_conn;       /* control block of connected socket */
        u_longlong_t unp_refs;       /* referencing socket linked list */
        u_longlong_t unp_nextref;    /* link in unp_refs list */
        u_longlong_t unp_addr;       /* bound address of socket */
};

struct m_hdr64
{
    u_longlong_t mh_next;            /* next buffer in chain */
    u_longlong_t mh_nextpkt;         /* next chain in queue/record */
    long mh_len;                     /* amount of data in this mbuf */
    u_longlong_t mh_data;            /* location of data */
};

struct mbuf64
{
    struct m_hdr64 m_hdr;
};

#define m_len               m_hdr.mh_len

#endif      /* __64BIT__ */
