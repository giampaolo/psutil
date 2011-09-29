import time
import curses

import psutil

def bytes2human(n):
    """
    >>> bytes2human(10000)
    '9.8K'
    >>> bytes2human(100001221)
    '95.4M'
    """
    assert isinstance(n, (int, long, float)), n
    if n == 0:
        return "0B"
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i+1)*10
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.2f %s' % (value, s)
#    return "0.0B " % n


def poll():
    # first get a list of all processes and disk io counters
    procs = [p for p in psutil.process_iter()]
    for p in procs[:]:
        try:
            p._before = p.get_io_counters()
        except psutil.Error:
            procs.remove(p)
            continue
    disks_before = psutil.disk_io_counters()

    # sleep some time
    time.sleep(1)

    # then retrieve the same info again
    for p in procs[:]:
        try:
            p._after = p.get_io_counters()
            p._cmdline = ' '.join(p.cmdline)
            if not p._cmdline:
                p._cmdline = p.name
            p._username = p.username
        except psutil.NoSuchProcess:
            procs.remove(p)
    disks_after = psutil.disk_io_counters()

    # finally calculate results by comparing data before and
    # after the interval
    for p in procs:
        p._read_per_sec = p._after.read_bytes - p._before.read_bytes
        p._write_per_sec = p._after.write_bytes - p._before.write_bytes
        p._total = p._read_per_sec + p._write_per_sec

    disks_read_per_sec = disks_after.read_bytes - disks_before.read_bytes
    disks_write_per_sec = disks_after.write_bytes - disks_before.write_bytes

    # sort processes by total IO
    processes = sorted(procs, key=lambda p: p._total, reverse=True)

    return (processes, disks_read_per_sec, disks_write_per_sec)


def run(myscreen):
    curses.endwin()
    templ = "%-5s %-7s %11s %11s  %s"
    while 1:
        procs, disks_read, disks_write = poll()
        myscreen.erase()
        #
        disks_tot = "Total DISK READ: %s | Total DISK WRITE: %s" \
                    % (bytes2human(disks_read), bytes2human(disks_write))
        myscreen.addstr(0, 0, disks_tot)
        #
        header = templ % ("PID", "USER", "DISK READ", "DISK WRITE", "COMMAND")
        header += " " * (myscreen.getmaxyx()[1] - len(header))
        myscreen.addstr(1, 0, header, curses.A_REVERSE)
        #
        lineno = 2
        for p in procs:
            line = templ % (p.pid,
                            p._username[:7],
                            bytes2human(p._read_per_sec) + '/s',
                            bytes2human(p._write_per_sec) + '/s',
                            p._cmdline)
            try:
                myscreen.addstr(lineno, 0, line)
            except curses.error:
                break
            myscreen.refresh()
            lineno += 1

def main():
    myscreen = curses.initscr()
    try:
        run(myscreen)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        curses.nocbreak(); myscreen.keypad(0); curses.echo()
        curses.endwin()

main()
