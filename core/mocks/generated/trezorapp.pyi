from typing import *
from buffer_types import *


# upymod/modtrezorapp/modtrezorapp-image.h
class AppError(Exception):
    """
    Base exception for all trezorapp errors.
    """


# upymod/modtrezorapp/modtrezorapp-image.h
class AppImageError(AppError):
    """
    Base exception for app image errors.
    """


# upymod/modtrezorapp/modtrezorapp-image.h
class AppImageNotFoundError(AppImageError):
    """
    Raised when the AppImage handle is invalid or the image no longer
    exists.
    """


# upymod/modtrezorapp/modtrezorapp-image.h
class AppImageMemoryError(AppImageError):
    """
    Raised when there is not enough memory in the app arena.
    """


# upymod/modtrezorapp/modtrezorapp-image.h
class AppImageVerificationError(AppImageError):
    """
    Raised when the app image data fails verification.
    """


# upymod/modtrezorapp/modtrezorapp-image.h
class AppArenaError(AppError):
    """
    Raised when an app arena operation fails.
    """


# upymod/modtrezorapp/modtrezorapp-image.h
class AppImage:
    """
    External application loaded in the app arena
    """

    def handle(self) -> int:
        """
        Return the image internal unique handle.
        """

    def task_id(self) -> int:
        """
        Return the task ID associated with the application image.
        """

    def is_running(self) -> bool:
        """
        Check if the application image is currently running.
        """

    def is_ready(self) -> bool:
        """
        Check if the application image has been fully loaded and verified.
        """

    def id(self) -> str:
        """
        Return the ID of the application image.
        """

    def size(self) -> int:
        """
        Return the size of the application image in bytes.
        """

    def chunk_size(self) -> int:
        """
        Return the expected size of each payload chunk in bytes.
        """

    def version(self) -> tuple[int, int, int, int]:
        """
        Return the version of the application image as a tuple (major, minor,
        patch, build).
        """

    def name(self) -> str:
        """
        Return the name of the application.
        """

    def vendor(self) -> str:
        """
        Return the vendor of the application.
        """

    def ring(self) -> int:
        """
        Return the privilege ring of the application.
        """

    def header_hash(self) -> bytes:
        """
        Return the hash of the application image header.
        """

    def write_chunk(self, data: AnyBytes, hash: AnyBytes) -> None:
        """
        Write a chunk of image data into app-arena memory.
        Allowed only while the image is in the loading state.
        """

    def delete(self) -> None:
        """
        Delete the application and release its resources.
        If the image is currently running, it is stopped before
        deletion. After deletion, the AppImage object is invalid
        and must not be used.
        """

    def run(self) -> int:
        """
        Run the loaded application image and return its task ID.
        If the image is already running, the function returns its task ID.
        Only ready images are runnable.
        """

    def stop(self) -> None:
        """
        Stop the running application image. If the image is not running,
        this operation has no effect.
        """

    def allowed_curves() -> Iterator[str]:
        """
        Return an iterator over the allowed curves
        """

    def allowed_paths() -> Iterator[str]:
        """
        Return an iterator over the allowed BIP32 path prefixes.
        """


# upymod/modtrezorapp/modtrezorapp.c
def create_image(header: AnyBytes, proof: AnyBytes) -> AppImage:
    """
    Create a new application image from header and proof.
    The returned handle can be used to load the rest of the
    image content and run it.
    """


# upymod/modtrezorapp/modtrezorapp.c
def images() -> Iterator[AppImage]:
    """
    Return an iterator over all app images in the app arena.
    """


# upymod/modtrezorapp/modtrezorapp.c
def image_by_handle(handle: int) -> AppImage:
    """
    Return the application image with the specified handle.
    """


# upymod/modtrezorapp/modtrezorapp.c
def clear_event() -> None:
    """
    Clear the pending event on the app arena, if any.
    """


# upymod/modtrezorapp/modtrezorapp.c
def image_count() -> int:
    """
    Return the number of application images currently
    loaded in the app arena.
    """


# upymod/modtrezorapp/modtrezorapp.c
def mem_total() -> int:
    """
    Return the total memory available in the app arena.
    """


# upymod/modtrezorapp/modtrezorapp.c
def mem_free() -> int:
    """
    Return the free memory available in the app arena.
    """


# upymod/modtrezorapp/modtrezorapp.c
def root_update(root_packet: AnyBytes) -> None:
    """
    Update the root-of-trust storage with the provided root packet.
    The root packet is verified for integrity and validity before being
    stored. If the verification fails, an AppArenaError is raised.
    """


# upymod/modtrezorapp/modtrezorapp.c
def root_is_loaded(ring: int) -> bool:
    """
    Return True if a root-of-trust is present for the specified ring,
    otherwise return False.
    """


# upymod/modtrezorapp/modtrezorapp.c
def root_timestamp(ring: int) -> int:
    """
    Return the timestamp of the root-of-trust for the specified ring.
    """


# upymod/modtrezorapp/modtrezorapp.c
def app_ring_from_header(header: AnyBytes) -> int:
    """
    Return the application privilege ring from the provided header.
    """
