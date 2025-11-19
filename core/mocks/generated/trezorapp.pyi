from typing import *
from buffer_types import *


# upymod/modtrezorapp/modtrezorapp-image.h
class AppImage:
    """
    Application image image.
    """

    def write(self, offset: int, data: AnyBytes) -> None:
        """
        Writes data to the application image at the specified offset.
        """

    def finalize(self, accept: bool) -> None:
        """
        Finalizes loading of the application image. If `accept` is true,
        the image is marked as loaded and will be available for execution.
        If `accept` is false, the image is discarded.
        """


# upymod/modtrezorapp/modtrezorapp-task.h
class AppTask:
    """
    App task structure.
    """

    def id(self) -> int:
        """
        Returns the task id.
        """

    def is_running(self) -> bool:
        """
        Returns whether the application is still running.
        """

    def unload(self) -> None:
        """
        Unloads the application associated with this task.
        """


# upymod/modtrezorapp/modtrezorapp.c
def spawn_task(app_hash: AnyBytes) -> AppTask:
    """
    Spawns an application task from the app cache.
    """


# upymod/modtrezorapp/modtrezorapp.c
def create_image(app_hash: AnyBytes, size: int) -> AppImage:
    """
    Creates a new application image in the app cache.
    """
