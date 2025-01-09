from __future__ import annotations

import typing as t
from concurrent.futures import ThreadPoolExecutor

import typing_extensions as tx

from trezorlib.client import PASSPHRASE_ON_DEVICE
from trezorlib.messages import DebugWaitType
from trezorlib.transport import udp

if t.TYPE_CHECKING:
    from trezorlib._internal.emulator import Emulator
    from trezorlib.debuglink import DebugLink
    from trezorlib.debuglink import TrezorClientDebugLink as Client
    from trezorlib.messages import Features

    P = tx.ParamSpec("P")


udp.SOCKET_TIMEOUT = 0.1


class NullUI:
    @staticmethod
    def button_request(code):
        pass

    @staticmethod
    def get_pin(code=None):
        raise NotImplementedError("NullUI should not be used with T1")

    @staticmethod
    def get_passphrase(available_on_device: bool = False):
        if available_on_device:
            return PASSPHRASE_ON_DEVICE
        else:
            raise NotImplementedError("NullUI should not be used with T1")


class BackgroundDeviceHandler:
    _pool = ThreadPoolExecutor()

    def __init__(self, client: "Client", nowait: bool = False) -> None:
        self._configure_client(client)
        self.task = None
        self.nowait = nowait

    def _configure_client(self, client: "Client") -> None:
        self.client = client
        self.client.ui = NullUI  # type: ignore [NullUI is OK UI]
        self.client.watch_layout(True)
        self.client.debug.input_wait_type = DebugWaitType.CURRENT_LAYOUT

    def run(
        self,
        function: t.Callable[tx.Concatenate["Client", P], t.Any],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        """Runs some function that interacts with a device.

        Makes sure the UI is updated before returning.
        """
        if self.task is not None:
            raise RuntimeError("Wait for previous task first")

        # wait for the first UI change triggered by the task running in the background
        with self.debuglink().wait_for_layout_change():
            self.task = self._pool.submit(function, self.client, *args, **kwargs)

    def kill_task(self) -> None:
        if self.task is not None:
            # Force close the client, which should raise an exception in a client
            # waiting on IO. Does not work over Bridge, because bridge doesn't have
            # a close() method.
            while self.client.session_counter > 0:
                self.client.close()
            try:
                self.task.result(timeout=1)
            except Exception:
                pass
        self.task = None

    def restart(self, emulator: "Emulator") -> None:
        # TODO handle actual restart as well
        self.kill_task()
        emulator.restart()
        self._configure_client(emulator.client)  # type: ignore [client cannot be None]

    def result(self, timeout: float | None = None) -> t.Any:
        if self.task is None:
            raise RuntimeError("No task running")
        try:
            return self.task.result(timeout=timeout)
        finally:
            self.task = None

    def features(self) -> "Features":
        if self.task is not None:
            raise RuntimeError("Cannot query features while task is running")
        self.client.init_device()
        return self.client.features

    def debuglink(self) -> "DebugLink":
        return self.client.debug

    def check_finalize(self) -> bool:
        if self.task is not None:
            self.kill_task()
            return False
        return True

    def __enter__(self) -> "BackgroundDeviceHandler":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        finalized_ok = self.check_finalize()
        if exc_type is None and not finalized_ok:
            raise RuntimeError("Exit while task is unfinished")
