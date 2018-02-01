'''Serial JSON. '''

from __future__ import print_function, unicode_literals

import re
import sys

try:
    CHR = unichr
except NameError:
    CHR = chr

# pylint: disable=too-few-public-methods
class Token(object):
    '''Base token class, used for Terminators and possibly more. '''
    def __str__(self):
        return '<{}>'.format(self.__class__.__name__)

class Terminator(Token):
    '''Signifies the beginning or end of a collection. '''
    pass

class ObjectTerminator(Terminator):
    '''Signifies the beginning or end of an object. '''
    pass

class ArrayTerminator(Terminator):
    '''Signifies the beginning or end of an array. '''
    pass

class StartTerminator(Terminator):
    '''Signifies the beginning of a collecction. '''
    pass

class EndTerminator(Terminator):
    '''Signifies the end of a collecction. '''
    pass

class StartObject(StartTerminator, ObjectTerminator):
    '''Signifies the beginning of an object. '''
    pass

class EndObject(EndTerminator, ObjectTerminator):
    '''Signifies the end of an object. '''
    pass

class StartArray(StartTerminator, ArrayTerminator):
    '''Signifies the beginning of an array. '''
    pass

class EndArray(EndTerminator, ArrayTerminator):
    '''Signifies the end of an array. '''
    pass

class Parser(object):
    '''Serial Parser for json files. '''
    digits = '-0123456789.'
    digits_terminator = '\t\n\r\f ,]}'
    key_pattern = re.compile(
        r'^[a-zA-Z][a-zA-Z0-9_]*$'
    )

    ws_pattern = re.compile(r'[ \t\n\r]*([^ \t\n\r])', re.MULTILINE)
    str_pattern = re.compile(r'([^"]*)"', re.MULTILINE)

    # parser mode contstants
    _NONE = 0
    _OBJECT = 1
    _LIST = 2

    escaped_chars = {
        '"': '"',
        "'": "'",
        '\\': '\\',
        'b': '\b',
        'f': '\f',
        'n': '\n',
        'r': '\r',
        't': '\t'
    }

    def __init__(self, file_object, terminators=False, rewind=True,
                 list_paths=False, encoding='utf-8', **kwargs):
        '''Constructor. 
        :param file_object: A file-like object to read.
        :param terminators: If true, yields terminators on beginning and end
                            of collections.
        :param rewind: Whether to seek the file-like object to 0 on load.
        :param list_paths: Yield paths as a list datatype rather than a
                           jsonpath.
        :param encoding: Encoding of the file object.
        '''
        self.start_object = StartObject()
        self.end_object = EndObject()
        self.start_array = StartArray()
        self.end_array = EndArray()

        self.terminators = terminators

        self.reader = file_object
        self.buffer_size = kwargs.pop('buffer_size', 1024)
        if kwargs:
            raise ValueError("Unrecognized arguments: '{}'".format(
                "', '".join(kwargs.keys())
            ))
        self._list_paths = list_paths
        self._encoding = encoding

        self._is_python2 = sys.version_info[0] < 3
        self._iter = None

        # parser variables
        self.buffer = ''
        self.buffer_offset = 0
        self._path = '$'
        if self._list_paths:
            self._path = ['$']
        self._part = '$'
        self._mode = 0
        self._parts = ['$']
        self._paths = [self._path]
        self._modes = [0]
        self.reset(rewind)

    def __iter__(self):
        for result in self._parse_value():
            yield result

    def __next__(self):
        return self.next()

    def next(self):
        '''Return next item from iterator'''
        if self._iter is None:
            self._iter = self._parse_value()
        return next(self._iter)

    def reset(self, rewind=True):
        '''Return the file pointer to the beginning of the file.
        NOTE: Not all data sources will support this.'''
        if rewind:
            self.reader.seek(0, 0)
        self.buffer = ''
        self.buffer_offset = 0

        self._path = '$'
        if self._list_paths:
            self._path = ['$']
        self._part = '$'
        self._mode = 0
        self._parts = ['$']
        self._paths = [self._path]
        self._modes = [0]

    def _parse_value(self):
        '''Read a value from a json file object. A value can be a number,
        string, null, object, or list. '''
        while True:
            char = self._read()
            if self._mode == self._OBJECT:
                if char == ',':
                    if self._part is None:
                        self.error("Syntax Error: Unexpected ','.")
                    self._part = None
                    continue
                elif char == '}':
                    self._exit_mode()
                    if self.terminators:
                        yield self._path, self.end_object
                    continue
                elif self._part is not None:
                    self.error("Syntax Error: Expected ',' ('{}')".format(
                        char
                    ))
                elif char != '"':
                    self.error("Syntax Error: Expected object key")
                key = self._parse_string(char)
                char = self._read()
                if char != ':':
                    self.error("Syntax Error: Expected ':'")
                self._update_mode(key)
                char = self._read()
            elif self._mode == self._LIST:
                if char == ',':
                    self._update_mode(self._part+1)
                    continue
                elif char == ']':
                    self._exit_mode()
                    if self.terminators:
                        yield self._path, self.end_array
                    continue
            if not char:
                if self._mode != self._NONE:
                    self.error("Unexpected end of file")
                break
            elif char == '{':
                if self.terminators:
                    yield self._path, self.start_object
                self._enter_mode(self._OBJECT, None)
            elif char == '[':
                if self.terminators:
                    yield self._path, self.start_array
                self._enter_mode(self._LIST, 0)
            elif char and char in self.digits:
                yield self._path, self._parse_number(char)
            elif char and char == '"':
                yield self._path, self._parse_string(char)
            elif char == 't' and self._read_chars(3) == 'rue':
                yield self._path, True
            elif char == 'f' and self._read_chars(4) == 'alse':
                yield self._path, False
            elif char == 'n' and self._read_chars(3) == 'ull':
                yield self._path, None
            elif char:
                self.error(
                    "Syntax Error: Unexpected character '{}'".format(char)
                )

    def error(self, message):
        '''Raises value error with path information. '''
        raise ValueError("[{}] {}".format(self._path, message))

    def _enter_mode(self, mode, part):
        '''Enters a nested scope (object or array). '''
        self._part = part
        self._parts.append(part)
        self._path = self._build_path(self._paths[-1], part)
        self._paths.append(self._path)
        self._mode = mode
        self._modes.append(mode)

    def _exit_mode(self):
        '''Leaves a nested scope. '''
        mode = self._modes.pop()
        self._parts.pop()
        self._paths.pop()
        self._path = self._paths[-1]
        self._part = self._parts[-1]
        self._mode = self._modes[-1]
        return mode

    def _update_mode(self, part):
        '''Travels laterally across a nested scope (change object keys or
        increment array indices).'''
        self._part = part
        self._parts[-1] = part
        if self._list_paths:
            self._path[-1] = part
        else:
            self._path = self._build_path(self._paths[-2], part)
            self._paths[-1] = self._path

    def _parse_string(self, quote):
        '''Returns a unicode string up to the quote (file pointer will be at
        the closing quote). '''
        output = []
        while True:
            # value = self._read_until(quote)
            match = self._read_until_pattern(self.str_pattern)
            if not match:
                break
            value = match.group(1)
            output.append(value)
            i = -1
            # TODO: Make this into a stringbuilder-esque class
            while abs(i) <= len(value) and value[i] == '\\':
                i -= 1
            if i % 2 == 1:
                break
            output.append(quote)
        if not output:
            return ''
        elif len(output) > 1:
            return self._deescape_string(''.join(output))
        return self._deescape_string(output[0])

    def _deescape_string(self, chars):
        '''Handled backslash-escaped characters. '''
        offset = chars.find('\\')
        buffer = []
        while offset != -1:
            buffer.append(chars[0:offset])
            escape_char = chars[offset+1]
            if escape_char in self.escaped_chars:
                buffer.append(self.escaped_chars[escape_char])
                chars = chars[offset+2:]
            elif escape_char == 'u':
                buffer.append(CHR(
                    int(chars[offset+2:offset+6], 16)
                ))
                chars = chars[offset+6:]
            else:
                buffer.append(chars[offset:offset+2])
                chars = chars[offset+2:]
            offset = chars.find('\\')
        buffer.append(chars)
        return ''.join(buffer)

    def _parse_number(self, char):
        '''Return a float from the buffer. The initial `char` is required as
        numbers do not have terminators so the first chaacter will be
        consumed. '''
        value = char + self._read_until(self.digits_terminator)
        return float(value)

    def _read(self):
        '''Reads one or more characters, returning the first that is not
        whitespace. '''
        match = self._read_pattern(self.ws_pattern)
        if not match:
            return ''
        return match.group(1)

    def _read_chars(self, length):
        '''Reads one or more characters, returning the first that is not
        whitespace. '''
        result = []
        while len(result) < length:
            if self.buffer_offset == len(self.buffer):
                self._fill_buffer()
            result.append(self.buffer[self.buffer_offset])
            self.buffer_offset += 1
        return ''.join(result)

    def _read_until(self, chars=None):
        '''Searches file from current pointer to one of character. '''
        min_end = -1
        result = []
        while True:
            for char in chars:
                pos = self.buffer.find(char, self.buffer_offset)
                if pos != -1:
                    if min_end == -1:
                        min_end = pos
                    else:
                        min_end = min([min_end, pos])
            if min_end != -1:
                result.append(self.buffer[self.buffer_offset:min_end])
                self.buffer_offset = min_end
                return ''.join(result)
            result.append(self.buffer[self.buffer_offset:])
            self._fill_buffer()
            if not self.buffer:
                return ''.join(result)

    def _read_pattern(self, pattern):
        '''Repeatedly applies the pattern to the current buffer (not file)
        until it returns a match. '''
        while True:
            match = pattern.match(self.buffer, self.buffer_offset)
            if match:
                self.buffer_offset += len(match.group(0))
                return match
            self._fill_buffer()
            if not self.buffer:
                return None

    def _read_until_pattern(self, pattern):
        '''Repeatedly applies the pattern to the current buffer (not file)
        until it returns a match. '''
        start = self.buffer_offset
        target = self.buffer
        while True:
            match = pattern.match(target, start)
            if match:
                self.buffer_offset = (
                    start + len(self.buffer) + len(match.group(0)) -
                    len(target))
                return match
            self._fill_buffer()
            if not self.buffer:
                return None
            target += self.buffer

    def _fill_buffer(self):
        '''Reads from file object into buffer. '''
        byte_buffer = self.reader.read(self.buffer_size)
        while True:
            try:
                if self._is_python2:
                    self.buffer = byte_buffer.decode(self._encoding)
                else:
                    self.buffer = byte_buffer
                break
            except UnicodeDecodeError:
                byte_buffer += self.reader.read(1)
        self.buffer_offset = 0

    def _build_path(self, prefix, path):
        '''Constructs a jsonpath given a current path and new part. '''
        if self._list_paths:
            return prefix + [path]
        if path is None:
            path = ''
        if isinstance(path, int):
            return '{}[{}]'.format(prefix, path)
        elif self.key_pattern.match(path):
            return '{}.{}'.format(prefix, path)
        return "{}['{}']".format(prefix, path)

def loads(json_string, *args, **kwargs):
    '''Load a json object via string. '''
    python2 = True
    try:
        from cStringIO import StringIO
    except ImportError:
        try:
            from StringIO import StringIO
        except ImportError:
            from io import StringIO
            python2 = False

    buffer = StringIO()
    if python2:
        import codecs
        codec = codecs.lookup("utf8")
        wrapper = codecs.StreamReaderWriter(
            buffer, codec.streamreader, codec.streamwriter)
        if isinstance(json_string, str):
            json_string = json_string.encode('utf-8')
        wrapper.write(json_string)
        wrapper.seek(0, 0)
        return Parser(wrapper, *args, **kwargs)
    buffer.write(json_string)
    buffer.seek(0, 0)

    return Parser(buffer, *args, **kwargs)

def load(json_file, *args, **kwargs):
    '''Load a json object via file object. '''
    return Parser(json_file, *args, **kwargs)
