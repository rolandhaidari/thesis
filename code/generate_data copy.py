#!/usr/bin/env python
import fcntl
import subprocess
import sys
from math import floor, log10
from random import choices, randrange, random
from uuid import uuid4
import os
import shutil
from datetime import datetime

STDOUT = 'output.csv'
STDERR = f'errlog-output.csv'


# parallel -j16 -- ./page-size-run.py {1} ::: $(seq 1 16)

def append(path, content):
    if content == '':
        return
    with open(path, 'a') as f:
        fcntl.lockf(f, fcntl.LOCK_EX)
        try:
            try:
                f.write(content)
            finally:
                f.flush()
        finally:
            fcntl.lockf(f, fcntl.F_UNLCK)

def archive():
    # Get the current date and time
    now = datetime.now()

    # Format the date and time
    date_time = now.strftime("%Y%m%d_%H:%M:%S")

    # Create the new directory
    new_dir = os.path.join("output", date_time)
    os.makedirs(new_dir, exist_ok=True)


    # Move STDOUT and STDERR to the new directory
    shutil.move(STDOUT, os.path.join(new_dir, STDOUT))
    shutil.move(STDERR, os.path.join(new_dir, STDERR))

starttime = datetime.now()
time_limit=60 # hours * minutes * seconds
i=0
while True:
    i+=1
    print("round: ", (i))

    # check if we have been running for more than 24 hours
    if (datetime.now() - starttime).total_seconds() > time_limit:
        print("time limit reached")
        break

    ycsb = choices(population=[3, 5], weights=[2, 1])[0]
    #data = choices(population=['rng4', 'int', 'data/urls-short', 'data/wiki'], weights=[1, 1, 1, 1])[0]
    data = 'data/urls'
    avg_key_size = {'data/urls': 62.280, 'rng4': 4, 'data/urls-short': 62.204, 'data/wiki': 22.555, 'int': 4}[data]
    max_key_count = {'data/urls': 6300000, 'data/urls-short': 6300000, 'data/wiki': 15000000, 'int': 4e9, 'rng4': 1e9}[
        data]
    lower = 8 if data == 'int' else 10
    psl_exp = 12  # randrange(lower, 16)
    psl = 2 ** psl_exp
    payload_size = 8 #randrange(0, 16) if random() < 0.75 else randrange(0, 256)
    target_total_size = 10 ** (random() * 0.5 + 8.25)
    density = 1 / 2 ** random()
    key_count = floor(target_total_size / (payload_size + avg_key_size))
    if key_count > max_key_count:
        print("key count too high")
        continue
    # config = choices(population='dense1 hash hints dense2 baseline prefix hot art adapt'.split())[0]
    config = choices(population='dense3 hints hash'.split())[0]

    if (config == 'dense1' or config == 'dense2') and data != 'int' and data != 'rng4':
        print("dense1 or dense2 with non-int data")
        continue
    if ycsb == 5 and config == 'hot':
        print("ycsb 5 with hot")
        continue
    path = f'btree-binaries/-DPS_I=4096 -DPS_L={psl}/{config}-n3-ycsb'
    env = {
        '_path': path,
        'RUN_ID': uuid4(),
        'YCSB_VARIANT': ycsb,
        'SCAN_LENGTH': 100,
        'OP_COUNT': '1e7',
        'DATA': data,
        'KEY_COUNT': key_count,
        'PAYLOAD_SIZE': payload_size,
        'ZIPF': -1,
        'DENSITY': density,
    }
    env = {k: str(env[k]) for k in env}
    try:
        process = subprocess.Popen(path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
        stdout, stderr = process.communicate()
        print("-----------------")
        if process.returncode != 0:
            raise RuntimeError(f'nonzero return code: {process.returncode}, stderr: {stderr}')
    except Exception as e:
        process.kill()
        stdout = ''
        stderr = f'exception: {e}\n'
        print("exception")
    append(STDOUT, stdout)
    append(STDERR, f'{env}\n{stderr}')

archive()



