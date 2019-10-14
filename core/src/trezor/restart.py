from trezor import loop, wire, workflow

if __debug__:
    from trezor import log
    from apps.debug import close_listeners


async def _perform_restart() -> None:
    if __debug__:
        log.debug(__name__, "restarting")
        await close_listeners()

    workflow.clear()
    loop.clear()
    wire.clear()


class no_return(loop.Syscall):
    def handle(self, task: loop.Task) -> None:
        pass


def restart() -> loop.Task:
    """
    Clears the loop state, leading to main.py
    performing the booting sequence again.
    """
    loop.schedule(_perform_restart())
    return no_return()
