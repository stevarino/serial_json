#!/usr/bin/python

import argparse
import resource
import time

import sejson

times = {}
class Timer(object):
    refs = {}
    times = {}
    def __init__(self, name):
        self.name = name
        self.refs[name] = self
        self.times[name] = (0,0)
    def __enter__(self):
        self.start = time.time()
        return self
    def __exit__(self, *args):
        end = time.time()
        total, cnt = self.times[self.name]
        self.times[self.name] = (
            total + end - self.start, 
            cnt + 1
        )

    @classmethod
    def timeit(cls, name, func, *args, **kwargs):
        timer = cls.refs.get(name)
        if not timer:
            timer = Timer(name)
        with timer:
            return func(*args, **kwargs)

    @classmethod
    def wrap(cls, name, func):
        timer = cls.refs.get(name)
        if not timer:
            timer = Timer(name)
        def wrapper(*args, **kwargs):
            with timer:
                return func(*args, **kwargs)
        return wrapper

timer_string = Timer('string')
timer_string1 = Timer('string1')
timer_string2 = Timer('string2')
timer_path = Timer('path')

parser = argparse.ArgumentParser()
parser.add_argument('file', help='File to parse')
parser.add_argument('--json', action='store_true')
parser.add_argument('--output', action='store_true')
parser.add_argument('--string', action='store_true')
parser.add_argument('--terminators', action='store_true')
parser.add_argument('--list_paths', action='store_true')
parser.add_argument('--wait', action='store_true')
parser.add_argument('--track', '-t', nargs='*')
args = parser.parse_args()

json_lib = sejson
if args.json:
    import json
    json_lib = json
with open(args.file, 'rb') as fp:
    start_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    start_time = time.time()
    data = fp
    json_func = json_lib.load
    if args.string:
        data = fp.read().decode('utf8')
        json_func = json_lib.loads
    kwargs = {}
    if args.terminators:
        kwargs['terminators'] = True
    if args.list_paths:
        kwargs['list_paths'] = True

    instance = json_func(data, **kwargs)

    if args.track:
        for item in args.track:
            instance.__setattr__(item, Timer.wrap(
                item, instance.__getattribute__(item)))

    for k in instance:
        if args.output:
            print(k)
    delta_m = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - start_mem
    delta_t = time.time() - start_time
    print('Total Memory:', delta_m)
    print('Total Time:', delta_t)
    if args.wait:
        raw_input("Press enter or Ctrl-C to exit.")
    for key in sorted(Timer.times):
        if Timer.times[key][1]:
            print('  {}: {}'.format(key, Timer.times[key]))
