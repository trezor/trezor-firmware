# Unit tests

Unit tests test some smaller individual parts of code (mainly functions and classes) and are run by micropython directly.

## Usage

Please use the unittest.TestCase class:

```python
from common import *

class TestSomething(unittest.TestCase):

    test_something(self):
        self.assertTrue(True)
```

Usage of `assert` is discouraged because it is not evaluated in production code (when `PYOPT=1`). Use `self.assertXY` instead, see `unittest.py`.
