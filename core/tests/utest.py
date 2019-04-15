import sys

__all__ = [
    'run_tests',
    'run_test',
    'assert_eq',
    'assert_not_eq',
    'assert_is_instance',
    'mock_call',
]


# Running


def run_tests(mod_name='__main__'):
    ntotal = 0
    nok = 0
    nfailed = 0

    for name, test in get_tests(mod_name):
        result = run_test(test)
        report_test(name, test, result)
        ntotal += 1
        if result:
            nok += 1
        else:
            nfailed += 1
            break
    report_total(ntotal, nok, nfailed)

    if nfailed > 0:
        sys.exit(1)


def get_tests(mod_name):
    module = __import__(mod_name)
    for name in dir(module):
        if name.startswith('test_'):
            yield name, getattr(module, name)


def run_test(test):
    try:
        test()
    except Exception as e:
        report_exception(e)
        return False
    else:
        return True


# Reporting


def report_test(name, test, result):
    if result:
        print('OK', name)
    else:
        print('ERR', name)


def report_exception(exc):
    sys.print_exception(exc)


def report_total(total, ok, failed):
    print('Total:', total, 'OK:', ok, 'Failed:', failed)


# Assertions


def assert_eq(a, b, msg=None):
    assert a == b, msg or format_eq(a, b)


def assert_not_eq(a, b, msg=None):
    assert a != b, msg or format_not_eq(a, b)


def assert_is_instance(obj, cls, msg=None):
    assert isinstance(obj, cls), msg or format_is_instance(obj, cls)


def assert_eq_obj(a, b, msg=None):
    assert_is_instance(a, b.__class__, msg)
    assert_eq(a.__dict__, b.__dict__, msg)


def format_eq(a, b):
    return '\n%r\nvs (expected)\n%r' % (a, b)


def format_not_eq(a, b):
    return '%r not expected to be equal %r' % (a, b)


def format_is_instance(obj, cls):
    return '%r expected to be instance of %r' % (obj, cls)


def assert_async(task, syscalls):
    for prev_result, expected in syscalls:
        if isinstance(expected, Exception):
            with assert_raises(expected.__class__):
                task.send(prev_result)
        else:
            syscall = task.send(prev_result)
            assert_eq_obj(syscall, expected)


class assert_raises:

    def __init__(self, exc_type):
        self.exc_type = exc_type

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        assert exc_type is not None, '%r not raised' % self.exc_type
        return issubclass(exc_type, self.exc_type)


class mock_call:

    def __init__(self, original, expected):
        self.original = original
        self.expected = expected
        self.record = []

    def __call__(self, *args):
        self.record.append(args)
        assert_eq(args, self.expected.pop(0))

    def assert_called_n_times(self, n, msg=None):
        assert_eq(len(self.record), n, msg)
