from typing import *
from buffer_types import *


# upymod/modtrezorapp/modtrezorapp-image.h
class AppImage:
    """
    Third-party application loaded or running in the app arena,
    a RAM region reserved for application images.
    """

    def get_handle(self) -> int
        """
        Returns the image internal unique handle.
        """

    def get_task_id(self) -> int:
        """
        Gets the task ID associated with the application image.
        """

    def is_running(self) -> bool:
        """
        Checks if the application image is currently running.
        """

    def is_verified(self) -> bool:
        """
        Checks if the application image has been verified.
        """

    def get_id(self) -> str:
        """
        Returns the ID of the application image.
        """

    def get_version(self) -> tuple[int, int]:
        """
        Returns the version of the application image as a tuple (major, minor).
        """

    def get_hash(self) -> bytes:
        """
        Returns the hash of the application image.
        """

    def write_chunk(self, data: AnyBytes) -> None:
        """
        Writes a chunk of image data into app-arena memory.
        Allowed only while the image is in the loading state.
        Call verify() after all chunks are written.
        """

    def verify(self, merkle_proof: AnyBytes) -> None:
        """
        Validates image integrity and verifies its signature.
        If verification succeeds, the image transitions to the
        verified state.
        """

    def delete(self) -> None:
        """
        Deletes the application and releases its resources.
        If the image is currently running, it is stopped before
        deletion. After deletion, the AppImage object is invalid
        and must not be used.
        """

    def run(self) -> int:
        """
        Runs the loaded application image. Only verified images
        are runnable. If the image is already running,
        this operation has no effect.
        """

    def stop(self) -> None:
        """
        Stops the running application image. If the image is not running,
        this operation has no effect.
        """


# upymod/modtrezorapp/modtrezorapp.c
def create_image() -> AppImage:
    """
    Creates a new empty application image. The returned handle
    can be used to load the image content and run it.
    """


# upymod/modtrezorapp/modtrezorapp.c
def get_image_by_index(idx: int) -> AppImage | None:
    """
    Returns the app image at the specified index in the app arena list.
    """


# upymod/modtrezorapp/modtrezorapp.c
def get_image_by_handle(handle: int) -> AppImage:
    """
    Returns the application image with the specified handle.
    """


# upymod/modtrezorapp/modtrezorapp.c
def clear_event() -> None:
    """
    Clears the pending event on the app arena, if any.
    """


# upymod/modtrezorapp/modtrezorapp.c
def get_image_count() -> int:
    """
    Returns the number of application images currently
    loaded in the app arena.
    """


# upymod/modtrezorapp/modtrezorapp.c
def get_mem_total() -> int:
    """
    Returns the total memory available in the app arena.
    """


# upymod/modtrezorapp/modtrezorapp.c
def get_mem_free() -> int:
    """
    Returns the free memory available in the app arena.
    """
