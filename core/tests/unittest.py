import sys

from trezor.utils import ensure


class SkipTest(Exception):
    pass


class AssertRaisesContext:

    def __init__(self, exc):
        self.expected = exc
        self.value = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            ensure(False, "%r not raised" % self.expected)
        if issubclass(exc_type, self.expected):
            self.value = exc_value
            return True
        return False


class TestCase:

    def fail(self, msg=''):
        ensure(False, msg)

    def assertEqual(self, x, y, msg=''):
        if not msg:
            msg = "%r vs (expected) %r" % (x, y)

        if x.__class__ == y.__class__ and x.__class__.__name__ == "Msg":
            self.assertMessageEqual(x, y)
        else:
            ensure(x == y, msg)

    def assertNotEqual(self, x, y, msg=''):
        if not msg:
            msg = "%r not expected to be equal %r" % (x, y)
        ensure(x != y, msg)

    def assertAlmostEqual(self, x, y, places=None, msg='', delta=None):
        if x == y:
            return
        if delta is not None and places is not None:
            raise TypeError("specify delta or places not both")

        if delta is not None:
            if abs(x - y) <= delta:
                return
            if not msg:
                msg = '%r != %r within %r delta' % (x, y, delta)
        else:
            if places is None:
                places = 7
            if round(abs(y - x), places) == 0:
                return
            if not msg:
                msg = '%r != %r within %r places' % (x, y, places)

        ensure(False, msg)

    def assertNotAlmostEqual(self, x, y, places=None, msg='', delta=None):
        if delta is not None and places is not None:
            raise TypeError("specify delta or places not both")

        if delta is not None:
            if not (x == y) and abs(x - y) > delta:
                return
            if not msg:
                msg = '%r == %r within %r delta' % (x, y, delta)
        else:
            if places is None:
                places = 7
            if not (x == y) and round(abs(y - x), places) != 0:
                return
            if not msg:
                msg = '%r == %r within %r places' % (x, y, places)

        ensure(False, msg)

    def assertIs(self, x, y, msg=''):
        if not msg:
            msg = "%r is not %r" % (x, y)
        ensure(x is y, msg)

    def assertIsNot(self, x, y, msg=''):
        if not msg:
            msg = "%r is %r" % (x, y)
        ensure(x is not y, msg)

    def assertIsNone(self, x, msg=''):
        if not msg:
            msg = "%r is not None" % x
        ensure(x is None, msg)

    def assertIsNotNone(self, x, msg=''):
        if not msg:
            msg = "%r is None" % x
        ensure(x is not None, msg)

    def assertTrue(self, x, msg=''):
        if not msg:
            msg = "Expected %r to be True" % x
        ensure(x, msg)

    def assertFalse(self, x, msg=''):
        if not msg:
            msg = "Expected %r to be False" % x
        ensure(not x, msg)

    def assertIn(self, x, y, msg=''):
        if not msg:
            msg = "Expected %r to be in %r" % (x, y)
        ensure(x in y, msg)

    def assertIsInstance(self, x, y, msg=''):
        ensure(isinstance(x, y), msg)

    def assertRaises(self, exc, func=None, *args, **kwargs):
        if func is None:
            return AssertRaisesContext(exc)
        try:
            func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, exc):
                return
            raise
        else:
            ensure(False, "%r not raised" % exc)

    def assertListEqual(self, x, y, msg=''):
        if len(x) != len(y):
            if not msg:
                msg = "List lengths not equal"
            ensure(False, msg)

        for i in range(len(x)):
            self.assertEqual(x[i], y[i], msg)

    def assertAsync(self, task, syscalls):
        for prev_result, expected in syscalls:
            if isinstance(expected, Exception):
                with self.assertRaises(expected.__class__):
                    task.send(prev_result)
            else:
                syscall = task.send(prev_result)
                self.assertObjectEqual(syscall, expected)

    def assertObjectEqual(self, a, b, msg=''):
        self.assertIsInstance(a, b.__class__, msg)
        self.assertEqual(a.__dict__, b.__dict__, msg)

    def assertMessageEqual(self, x, y):
        self.assertEqual(
            x.MESSAGE_NAME,
            y.MESSAGE_NAME,
            "Expected {}, found {}".format(x.MESSAGE_NAME, y.MESSAGE_NAME)
        )
        xdict = x.__dict__
        ydict = y.__dict__
        for key in xdict:
            self.assertTrue(key in ydict)
            self.assertEqual(
                xdict[key],
                ydict[key],
                "At {}.{} expected {}, found {}".format(x.MESSAGE_NAME, key, xdict[key], ydict[key])
            )


def skip(msg):
    def _decor(fun):
        # We just replace original fun with _inner
        def _inner(self):
            raise SkipTest(msg)
        return _inner
    return _decor


def skipUnless(cond, msg):
    if cond:
        return lambda x: x
    return skip(msg)


class TestSuite:

    def __init__(self):
        self.tests = []

    def addTest(self, cls):
        self.tests.append(cls)


class TestRunner:

    def run(self, suite):
        res = TestResult()
        for c in suite.tests:
            run_class(c, res)
        return res


class TestResult:

    def __init__(self):
        self.errorsNum = 0
        self.failuresNum = 0
        self.skippedNum = 0
        self.testsRun = 0

    def wasSuccessful(self):
        return self.errorsNum == 0 and self.failuresNum == 0


generator_type = type((lambda: (yield))())


def run_class(c, test_result):
    o = c()
    set_up = getattr(o, "setUp", lambda: None)
    tear_down = getattr(o, "tearDown", lambda: None)
    print('class', c.__qualname__)
    for name in dir(o):
        if name.startswith("test"):
            print(' ', name, end=' ...')
            m = getattr(o, name)
            try:
                try:
                    set_up()
                    test_result.testsRun += 1
                    retval = m()
                    if isinstance(retval, generator_type):
                        raise RuntimeError("{} must not be a generator (it is async, uses yield or await).".format(name))
                    elif retval is not None:
                        raise RuntimeError("{} should not return a result.".format(name))
                finally:
                    tear_down()
                print(" ok")
            except SkipTest as e:
                print(" skipped:", e.args[0])
                test_result.skippedNum += 1
            except AssertionError as e:
                print(" failed")
                sys.print_exception(e)
                test_result.failuresNum += 1
            except BaseException as e:
                print(" errored:", e)
                sys.print_exception(e)
                test_result.errorsNum += 1


def main(module="__main__"):
    def test_cases(m):
        for tn in dir(m):
            c = getattr(m, tn)
            if isinstance(c, object) and isinstance(c, type) and issubclass(c, TestCase):
                yield c

    m = __import__(module)
    suite = TestSuite()
    for c in test_cases(m):
        suite.addTest(c)
    runner = TestRunner()
    result = runner.run(suite)
    msg = "Ran %d tests" % result.testsRun
    result_strs = []
    if result.skippedNum > 0:
        result_strs.append("{} skipped".format(result.skippedNum))
    if result.failuresNum > 0:
        result_strs.append("{} failed".format(result.failuresNum))
    if result.errorsNum > 0:
        result_strs.append("{} errored".format(result.errorsNum))
    if result_strs:
        msg += " (" + ", ".join(result_strs) + ")"
    print(msg)

    if not result.wasSuccessful():
        raise SystemExit(1)
