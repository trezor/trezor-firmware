import uselect
import errno

from .core import EventLoop

if __debug__:
    import logging
    log = logging.getLogger("asyncio")

class EpollEventLoop(EventLoop):

    def __init__(self):
        EventLoop.__init__(self)
        self.poller = uselect.poll()
        self.objmap = {}

    def add_reader(self, fd, cb, *args):
        if __debug__:
            log.debug("add_reader%s", (fd, cb, args))
        if args:
            self.poller.register(fd, uselect.POLLIN)
            self.objmap[fd] = (cb, args)
        else:
            self.poller.register(fd, uselect.POLLIN)
            self.objmap[fd] = cb

    def remove_reader(self, fd):
        if __debug__:
            log.debug("remove_reader(%s)", fd)
        self.poller.unregister(fd)
        del self.objmap[fd]

    def add_writer(self, fd, cb, *args):
        if __debug__:
            log.debug("add_writer%s", (fd, cb, args))
        if args:
            self.poller.register(fd, uselect.POLLOUT)
            self.objmap[fd] = (cb, args)
        else:
            self.poller.register(fd, uselect.POLLOUT)
            self.objmap[fd] = cb

    def remove_writer(self, fd):
        if __debug__:
            log.debug("remove_writer(%s)", fd)
        try:
            self.poller.unregister(fd)
            self.objmap.pop(fd, None)
        except OSError as e:
            # StreamWriter.awrite() first tries to write to an fd,
            # and if that succeeds, yield IOWrite may never be called
            # for that fd, and it will never be added to poller. So,
            # ignore such error.
            if e.args[0] != errno.ENOENT:
                raise

    def wait(self, delay):
        if __debug__:
            log.debug("epoll.wait(%d)", delay)
        # We need one-shot behavior (second arg of 1 to .poll())
        if delay == -1:
            res = self.poller.poll(-1, 1)
        else:
            res = self.poller.poll(int(delay * 1000), 1)
        # log.debug("epoll result: %s", res)
        for fd, ev in res:
            cb = self.objmap[fd]
            if __debug__:
                log.debug("Calling IO callback: %r", cb)
            if isinstance(cb, tuple):
                cb[0](*cb[1])
            else:
                self.call_soon(cb)
