import utime
import uheapq

from .utils import type_gen

if __debug__:
    import logging
    log = logging.getLogger("trezor.loop")

q = []
cnt = 0
last_sleep = 0  # For performance stats

def call_soon(callback, *args):
    call_at(0, callback, *args)

def call_later(delay, callback, *args):
    call_at(utime.ticks_us() + delay, callback, *args)

def call_at(time, callback, *args):
    global cnt

    if __debug__:
        log.debug("Scheduling %s", (int(time), cnt, callback, args))
    # Including self.cnt is a workaround per heapq docs
    uheapq.heappush(q, (int(time), cnt, callback, args))

    cnt += 1

def wait(delay):
    global last_sleep

    if __debug__:
        log.debug("Sleeping for: %s", delay)

    last_sleep = delay
    utime.sleep_us(delay)

def run_forever():
    global q, cnt

    while True:
        if q:
            t, cnt, cb, args = uheapq.heappop(q)
            if __debug__:
                log.debug("Next coroutine to run: %s", (t, cnt, cb, args))
            tnow = utime.ticks_us()
            delay = t - tnow
            if delay > 0:
                wait(delay)
        else:
            wait(-1)
            # Assuming IO completion scheduled some tasks
            continue
        if callable(cb):
            ret = cb(*args)
            if __debug__ and isinstance(ret, type_gen):
                log.warning("Callback produced generator, which will never run.")
        else:
            delay = 0
            try:
                if args == ():
                    args = (None,)
                if __debug__:
                    log.debug("Coroutine %s send args: %s", cb, args)
                ret = cb.send(*args)
                if __debug__:
                    log.debug("Coroutine %s yield result: %s", cb, ret)
                if isinstance(ret, SysCall1):
                    arg = ret.arg
                    if isinstance(ret, Sleep):
                        delay = arg
                    elif isinstance(ret, StopLoop):
                        return arg
                    # elif isinstance(ret, IORead):
                    #    self.add_reader(arg.fileno(), lambda self, c, f: self.call_soon(c, f), self, cb, arg)
                    #    self.add_reader(arg.fileno(), lambda c, f: self.call_soon(c, f), cb, arg)
                    #    self.add_reader(arg.fileno(), lambda cb: self.call_soon(cb), cb)
                    #    self.add_reader(arg.fileno(), cb)
                    #    continue
                    # elif isinstance(ret, IOWrite):
                    #    self.add_writer(arg.fileno(), lambda cb: self.call_soon(cb), cb)
                    #    self.add_writer(arg.fileno(), cb)
                    #    continue
                    # elif isinstance(ret, IOReadDone):
                    #    self.remove_reader(arg.fileno())
                    # elif isinstance(ret, IOWriteDone):
                    #    self.remove_writer(arg.fileno())

                elif isinstance(ret, type_gen):
                    call_soon(ret)
                elif ret is None:
                    # Just reschedule
                    pass
                else:
                    assert False, "Unsupported yield value: %r (of type %r)" % (ret, type(ret))
            except StopIteration as e:
                if __debug__:
                    log.debug("Coroutine finished: %s", cb)
                continue
            call_later(delay, cb, *args)

# def run_until_complete(self, coro):
#    def _run_and_stop():
#        yield from coro
#        yield StopLoop(0)
#    self.call_soon(_run_and_stop())
#    self.run_forever()
# class SysCall:
#    def __init__(self, *args):
#        self.args = args
#    def handle(self):
#        raise NotImplementedError
    
# Optimized syscall with 1 arg
class SysCall1:
    def __init__(self, arg):
        self.arg = arg

    def handle(self):
        raise NotImplementedError

#class IOButton(SysCall):
#    pass

class StopLoop(SysCall1):
    pass

class Sleep(SysCall1):
    pass

# class IORead(SysCall1):
#    pass

# class IOWrite(SysCall1):
#    pass

# class IOReadDone(SysCall1):
#    pass

# class IOWriteDone(SysCall1):
#    pass

# _event_loop = None
# _event_loop_class = EventLoop
# def get_event_loop():
#    global _event_loop
#    if _event_loop is None:
#        _event_loop = _event_loop_class()
#    return _event_loop
