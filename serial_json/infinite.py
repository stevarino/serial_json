from __future__ import print_function, unicode_literals

from datetime import datetime
import time

import sejson


class InfiniteStream(object):
    def __init__(self):
        self.is_initialized = False

    def read(self, size=None):
        '''Starts an object stream and returns a field for the time. '''
        if not self.is_initialized:
            self.is_initialized = True
            return '{'
        time.sleep(1)
        return '"now": "{}",'.format(datetime.now())

    def seek(self, *args):
        pass

while True:
    parser = sejson.load(InfiniteStream())
    for key, value in parser:
        print(key, value)
