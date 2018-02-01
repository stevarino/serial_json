import argparse
from collections import OrderedDict
import json
import os.path as path
import resource
import time

import serial_json

examples = OrderedDict()
[OrderedDict.__setitem__(examples, e[0], e[1]) for e in [
    ('all', ''),
    ('us_house', 'ep-us-house.json')
]]

def run_example(example, parser=None):
    with open(path.join(path.dirname(__file__), 'data', example)) as fp:

        start_mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        start_time = time.time()
        for k in parser(fp):
            pass
        delta_m = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - start_mem
        delta_t = time.time() - start_time
        print delta_t, delta_m

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('example', choices=examples.keys())
    parser.add_argument('--use_json', action='store_true')
    args = parser.parse_args()


    json_parser = serial_json.load
    if args.use_json:
        json_parser = json.load
    example = examples[args.example]
    if example:
        run_example(example, json_parser)
    else:
        for key in examples:
            if examples[key]:
                print key
                run_example(examples[key], json_parser)
    

