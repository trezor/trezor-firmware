from concurrent.futures import ThreadPoolExecutor


class NullUI:
    @staticmethod
    def button_request(code):
        pass

    @staticmethod
    def get_pin(code=None):
        raise NotImplementedError("Should not be used with T1")

    @staticmethod
    def get_passphrase():
        raise NotImplementedError("Should not be used with T1")


class BackgroundDeviceHandler:
    _pool = ThreadPoolExecutor()

    def __init__(self, client):
        self.client = client
        self.client.ui = NullUI
        self.task = None

    def run(self, function, *args, **kwargs):
        if self.task is not None:
            raise RuntimeError("Wait for previous task first")
        self.task = self._pool.submit(function, self.client, *args, **kwargs)

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
            self.task.cancel()
            self.task = None
            return False
        return True
