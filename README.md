# Serial Json

A SAX-like serial json reader similar to [ijson](https://pypi.python.org/pypi/ijson/) but written in pure Python. Supports the following features:

 - Python2/3 compatible. No external binary or package requirements needed.
 - O(n) time and O(1) memory usage. In fact most uses will be memory cost-free due to recycling. Typical speed tests are in the range of 10-15x slower than native.
 - Single-pass read. No rewinding/seeking required, very small memory footprint.
 - Receive JSON data via a `(path, value)` yielding iterator.
 - Paths can be either jsonpath-style strings or native lists for easier parsing.
 - Optionally yield collection terminators - useful if empty collections are important.
 - Flexible input - requires only a file-like object that supports `read` and (optionally) `seek`. An infinite json "file" can be parsed with this.

Created as a self-challenge to write a python parser for extremely large files (>500MB) as the native `json` library will require substantially more memory.
