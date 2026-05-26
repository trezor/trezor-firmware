from __future__ import annotations

import typing as t
from concurrent.futures import ThreadPoolExecutor

import typing_extensions as tx

from ..messages import DebugWaitType
from ..transport import udp

if t.TYPE_CHECKING:
    from .._internal.emulator import Emulator
    from ..client import Session
    from ..debuglink import DebugLink
    from ..debuglink import TrezorTestContext as Client
    from ..messages import Features

    P = tx.ParamSpec("P")


udp.SOCKET_TIMEOUT = 0.1


class NullUI:
    """
    A mock UI class for testing purposes.

    Provides static methods that do nothing or raise errors, simulating
    a UI interface for use in tests where UI interaction is not expected.
    """

    @staticmethod
    def clear(*args: t.Any, **kwargs: t.Any) -> None:
        """
        Mock clear method. Does nothing.
        """

    @staticmethod
    def button_request(code: t.Any) -> None:
        """
        Mock button request handler. Does nothing.
        """

    @staticmethod
    def get_pin(code: t.Any = None) -> None:
        """
        Mock PIN entry handler.

        Raises:
            NotImplementedError: Always, as PIN entry should not be used with NullUI.
        """
        raise NotImplementedError("NullUI should not be used with T1")


class BackgroundDeviceHandler:
    """
    Handles background operations and UI simulation for device testing.

    Manages asynchronous device interactions, session handling, and UI events
    in a testing environment. Ensures that device tasks are properly started,
    awaited, and finalized.
    """

    _pool = ThreadPoolExecutor()

    def __init__(self, client: "Client", nowait: bool = False) -> None:
        """
        Initialize the handler with a client.

        Args:
            client: The client object to interact with.
            nowait: If True, do not wait for tasks to finish before returning.
        """
        self._configure_client(client)
        self.task = None
        self.nowait = nowait

    def _configure_client(self, client: "Client") -> None:
        """
        Configure the client for background handling and set up the mock UI.

        Args:
            client: The client object to configure.
        """
        self.client = client
        self.client.ui = NullUI()  # pyright: ignore [reportAttributeAccessIssue]
        self.client.app.button_callback = self.client.ui.button_request
        self.client.debug.input_wait_type = DebugWaitType.CURRENT_LAYOUT

    def get_session(self, *args: t.Any, **kwargs: t.Any) -> None:
        """
        Start a background task to get a session, waiting for a layout change.

        Raises:
            RuntimeError: If a previous task is still running.
        """
        if self.task is not None:
            raise RuntimeError("Wait for previous task first")

        with self.debuglink().wait_for_layout_change():
            self.task = self._pool.submit(self.client.get_session, *args, **kwargs)

    def run_with_session(
        self,
        function: t.Callable[tx.Concatenate["Session", P], t.Any],
        seedless: bool = False,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        """
        Run a function that interacts with a device session in the background.

        Ensures the UI is updated before returning.

        Args:
            function: The function to run with the session.
            seedless: If True, use a seedless session.
            *args: Additional positional arguments for the function.
            **kwargs: Additional keyword arguments for the function.

        Raises:
            RuntimeError: If a previous task is still running.
        """
        if self.task is not None:
            raise RuntimeError("Wait for previous task first")

        def task_function(*args: t.Any, **kwargs: t.Any) -> t.Any:
            if seedless:
                session = self.client.get_seedless_session()
            else:
                session = self.client.get_session()
            return function(session, *args, **kwargs)

        # wait for the first UI change triggered by the task running in the background
        with self.debuglink().wait_for_layout_change():
            self.task = self._pool.submit(task_function, *args, **kwargs)

    def run_with_provided_session(
        self,
        session: "Session",
        function: t.Callable[tx.Concatenate["Session", P], t.Any],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        """
        Run a function with a provided session in the background.

        Ensures the UI is updated before returning.

        Args:
            session: The session to use.
            function: The function to run.
            *args: Additional positional arguments for the function.
            **kwargs: Additional keyword arguments for the function.

        Raises:
            RuntimeError: If a previous task is still running.
        """
        if self.task is not None:
            raise RuntimeError("Wait for previous task first")

        # wait for the first UI change triggered by the task running in the background
        with self.debuglink().wait_for_layout_change():
            self.task = self._pool.submit(function, session, *args, **kwargs)

    def kill_task(self) -> None:
        """
        Kill the currently running background task, if any.

        Closes the client transport and waits for the task to finish.
        """
        if self.task is not None:
            # Force close the transport, which should raise an exception in a client
            # waiting on IO. Does not work over Bridge, because bridge doesn't have
            # a close() method.
            self.client.transport.close()
            try:
                self.task.result(timeout=1)
            except Exception:
                pass
        self.task = None

    def restart(self, emulator: "Emulator") -> None:
        """
        Restart the emulator and reconfigure the client.

        Args:
            emulator: The emulator to restart.
        """
        # TODO handle actual restart as well
        self.kill_task()
        emulator.restart()
        self._configure_client(emulator.client)

    def result(self, timeout: float | None = None) -> t.Any:
        """
        Get the result of the background task.

        Args:
            timeout: Optional timeout in seconds.

        Returns:
            The result of the task.

        Raises:
            RuntimeError: If no task is running.
        """
        if self.task is None:
            raise RuntimeError("No task running")
        try:
            return self.task.result(timeout=timeout)
        finally:
            self.task = None

    def features(self) -> "Features":
        """
        Refresh and return the client's features.

        Returns:
            Features: The client's features.

        Raises:
            RuntimeError: If a task is running.
        """
        if self.task is not None:
            raise RuntimeError("Cannot query features while task is running")
        self.client.refresh_features()
        return self.client.features

    def debuglink(self) -> "DebugLink":
        """
        Get the debuglink for the client.

        Returns:
            DebugLink: The client's debuglink.
        """
        return self.client.debug

    def check_finalize(self) -> bool:
        """
        Ensure all tasks are finalized.

        Returns:
            bool: True if no task was running, False if a task was killed.
        """
        if self.task is not None:
            self.kill_task()
            return False
        return True

    def __enter__(self) -> "BackgroundDeviceHandler":
        """
        Enter the context manager.

        Returns:
            BackgroundDeviceHandler: self
        """
        return self

    def __exit__(self, exc_type: t.Any, exc_value: t.Any, traceback: t.Any) -> None:
        """
        Exit the context manager, ensuring all tasks are finalized.

        Raises:
            RuntimeError: If exiting while a task is unfinished.
        """
        finalized_ok = self.check_finalize()
        if exc_type is None and not finalized_ok:
            raise RuntimeError("Exit while task is unfinished")
