from concurrent.futures import ThreadPoolExecutor

from trezorlib.client import PASSPHRASE_ON_DEVICE
from trezorlib.transport import udp

udp.SOCKET_TIMEOUT = 0.1


class NullUI:
    @staticmethod
    def button_request(code):
        pass

    @staticmethod
    def get_pin(code=None):
        raise NotImplementedError("NullUI should not be used with T1")

    @staticmethod
    def get_passphrase(available_on_device=False):
        if available_on_device:
            return PASSPHRASE_ON_DEVICE
        else:
            raise NotImplementedError("NullUI should not be used with T1")


class BackgroundDeviceHandler:
    _pool = ThreadPoolExecutor()

    def __init__(self, client):
        self._configure_client(client)
        self.task = None

    def _configure_client(self, client):
        self.client = client
        self.client.ui = NullUI
        self.client.watch_layout(True)

    def run(self, function, *args, **kwargs):
        if self.task is not None:
            raise RuntimeError("Wait for previous task first")
        self.task = self._pool.submit(function, self.client, *args, **kwargs)

    def kill_task(self):
        if self.task is not None:
            # Force close the client, which should raise an exception in a client
            # waiting on IO. Does not work over Bridge, because bridge doesn't have
            # a close() method.
            while self.client.session_counter > 0:
                self.client.close()
            try:
                self.task.result()
            except Exception:
                pass
        self.task = None

    def restart(self, emulator):
        # TODO handle actual restart as well
        self.kill_task()
        emulator.restart()
        self._configure_client(emulator.client)

    def result(self):
        if self.task is None:
            raise RuntimeError("No task running")
        try:
            return self.task.result()
        finally:
            self.task = None

    def features(self):
        if self.task is not None:
            raise RuntimeError("Cannot query features while task is running")
        self.client.init_device()
        return self.client.features

    def debuglink(self):
        return self.client.debug

    def check_finalize(self):
        if self.task is not None:
            self.kill_task()
            return False
        return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        finalized_ok = self.check_finalize()
        if exc_type is None and not finalized_ok:
            raise RuntimeError("Exit while task is unfinished")
