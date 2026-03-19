import os
import tempfile

import pytest

from ..emulators import stop_shared_tropic_model


@pytest.fixture
def shared_profile_dir():
    keep_profile = os.environ.get("TREZOR_KEEP_PROFILE_DIR") == "1"
    profile_dir = tempfile.TemporaryDirectory()
    # TODO: in Python >=3.12, simplify to
    # with tempfile.TemporaryDirectory(delete=not keep_profile) as path:
    #    yield path          # str, not TemporaryDirectory

    if keep_profile:
        # Prevent automatic cleanup when the object is GC'd.
        finalizer = getattr(profile_dir, "_finalizer", None)
        if finalizer is not None:
            try:
                finalizer.detach()
            except AttributeError:
                pass

    try:
        yield profile_dir
    finally:
        if not keep_profile:
            profile_dir.cleanup()


@pytest.fixture(autouse=True)
def _cleanup_shared_tropic_model(shared_profile_dir):
    """Stop any shared Tropic model that was started during the test."""
    yield
    stop_shared_tropic_model(shared_profile_dir.name)
