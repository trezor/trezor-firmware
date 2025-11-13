from trezor.messages import ExtAppLoad, ExtAppLoaded, Failure
from trezor.crypto.hashlib import sha256


async def load(msg: ExtAppLoad) -> ExtAppLoaded | Failure:
    from trezor import app

    """Load external application from a host path and return its hash.

    Note: On emulator, `msg.path` should point to the .so file on the host filesystem.
    This handler currently computes and returns the binary hash; the actual loading
    is performed when the app is spawned (see extapp.run and app_cache).
    """
    try:
        path = msg.path or ""
        h = sha256()
        # Read the file and compute SHA-256 digest
        with open(path, "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                h.update(chunk)
        final_hash = h.digest()
        app.load_file(final_hash, path)
        return ExtAppLoaded(hash=final_hash)
    except Exception as e:
        return Failure(message=f"ExtApp load failed: {e}")
