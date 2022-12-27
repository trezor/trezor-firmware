# pyright: reportGeneralTypeIssues=false
import gc

if __debug__:
    from trezor import log

    def log_gc(label=""):
        gc.collect()
        log_gc_2(label)

    def log_gc_2(label=""):
        log.info(
            __name__,
            "GC[%s]: alloc: %d kb, free: %d kb (%d/1000)",
            label,
            gc.mem_alloc() // 1000,  # type: ignore
            gc.mem_free() // 1000,  # type: ignore
            (1000 * gc.mem_free()) // (gc.mem_free() + gc.mem_alloc()),  # type: ignore
        )

    def trace_gc(x):
        gc.collect()
        log_gc_2("trace")
        gc.collect()
        return x


def watch_gc(func):
    if __debug__:

        def wrapper(*args, **kwargs):
            log_gc("before " + func.__name__)
            res = func(*args, **kwargs)
            log_gc("after " + func.__name__)
            return res

        return wrapper
    else:
        return func


def watch_gc_async(func):
    if __debug__:

        async def wrapper(*args, **kwargs):
            log_gc("before " + func.__name__)
            res = await func(*args, **kwargs)
            log_gc("after " + func.__name__)
            return res

        return wrapper
    else:
        return func
