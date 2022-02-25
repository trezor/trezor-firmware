# Unit tests

Unit tests test some smaller individual parts of code (mainly functions and classes) and are run by micropython directly.

## How to run them

Run all tests:
```sh
make test
```

Run a specific test file:
```sh
make test TESTOPTS=test_apps.bitcoin.signtx.py
```

__WARNING__: unittests cannot run with frozen emulator, use `make build_unix` to create non-frozen emulator.

## Usage

Please use the unittest.TestCase class:

```python
from common import *

class TestSomething(unittest.TestCase):

    test_something(self):
        self.assertTrue(True)
```

Usage of `assert` is discouraged because it is not evaluated in production code (when `PYOPT=1`). Use `self.assertXY` instead, see `unittest.py`.
