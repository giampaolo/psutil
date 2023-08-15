#!/usr/bin/env python3

# The script makes a system trace based on Trace Event Format:
# https://docs.google.com/document/d/1CvAClvFfyA5R-PhYUmn5OOQtYMH4h6I0nSsKchNAySU/preview#heading=h.yr4qxyxotyw
#
# that can be opened in https://ui.perfetto.dev/ for inspection.

import json
import time

import psutil


OUTPUT_FILE = 'trace.json'
INTERVAL = 0.25

trace_data = []

# initial values
vm_initial = psutil.virtual_memory()
last_disk_counters = [0, 0]
last_net_counters = [0, 0]

start = time.time()


def convert_time(t):
    return t * 10**6


try:
    while True:
        # CPU
        cpu_percent = psutil.cpu_percent(percpu=False, interval=INTERVAL)
        ts = convert_time(time.time())
        trace_data.append({'name': 'CPU usage', 'category': 'CPU', 'ph': 'C',
                           'ts': ts, 'args': {'average': cpu_percent}})

        # USED MEMORY
        used = psutil.virtual_memory().used
        trace_data.append({'name': 'Used memory', 'category': 'Memory',
                           'ph': 'C', 'ts': ts,
                           'args': {'bytes': max(0, used - vm_initial.used)}})

        # DISK USAGE
        disk_counters = psutil.disk_io_counters()
        read_value = disk_counters.read_bytes
        write_value = disk_counters.write_bytes

        first = last_disk_counters[0] == 0
        read_per_sec = (read_value - last_disk_counters[0]) / INTERVAL
        write_per_sec = (write_value - last_disk_counters[1]) / INTERVAL
        last_disk_counters = [read_value, write_value]
        if not first:
            trace_data.append({'name': 'Disk (bytes/s)', 'category': 'Disk',
                               'ph': 'C', 'ts': ts,
                               'args': {'read': read_per_sec,
                                        'write': write_per_sec}})
        # NETWORK USAGE
        net_counters = psutil.net_io_counters()
        received_value = net_counters.bytes_recv
        sent_value = net_counters.bytes_sent

        first = last_net_counters[0] == 0
        received_per_sec = (received_value - last_net_counters[0]) / INTERVAL
        sent_per_sec = (sent_value - last_net_counters[1]) / INTERVAL
        last_net_counters = [received_value, sent_value]
        if not first:
            trace_data.append({'name': 'Network (bytes/s)',
                               'category': 'Network',
                               'ph': 'C', 'ts': ts,
                               'args': {'received': received_per_sec,
                                        'sent': sent_per_sec}})


except KeyboardInterrupt:
    pass

with open(OUTPUT_FILE, 'w') as f:
    print(f'\nSaving output to: {OUTPUT_FILE}')
    f.write(json.dumps({'traceEvents': trace_data}))
