import os
import psutil
import time
import sys

if len(sys.argv) != 2:
    print("%s : %s [PROGRAM]" % (sys.argv[0], sys.argv[0]))
    exit(1)

env = os.environ.copy()
args = [sys.argv[1]]
p = psutil.Popen(args, env=env)
while p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
    print(p.threads())
    time.sleep(0.01)
