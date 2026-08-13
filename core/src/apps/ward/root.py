"""The trie root the device verifies proofs against.

A proof only means something when checked against a root the host did not choose. This
holds that root, in the SESSION CACHE.

Two reasons it must live there rather than in a module global, and the first is fatal:

  - Module state does not survive a workflow. `trezor.wire` wraps every request in
    `utils.unimport_begin()` / `unimport_end()`, which deletes from `sys.modules` every
    module the workflow imported. A root stashed in a module attribute is gone by the
    time the next request arrives, so it would silently read back as "no root" -- i.e.
    as "cannot verify", which fails open in the sense that nothing gets checked.
  - The session is also the right LIFETIME. K_path is passphrase-dependent, so each
    hidden wallet has its own trie and therefore its own root; a root shared across
    sessions would belong to whichever wallet happened to set it last.

FIXME(ward, TRANSITIONAL): the root is only settable by `WARDDebugSetRoot` in a debug
build, and does not survive a restart. Making it permanent means persisting it, and a
root worth persisting has to be an ATTESTED one -- otherwise the device is storing a
number it was simply handed. That arrives with the freshness round; this exists so the
verification path can be wired and tested before then.

WHAT A ROOT HERE DOES AND DOES NOT PROVE. Given one, the device can reject a leaf the
host forged, edited, moved between paths, or invented, and can reject a claim of absence
for an entry that exists. It CANNOT tell whether the root itself is current -- a host
that also rolled the device back to an older root would present a perfectly consistent
older world. Only an attested root closes that, so the screens still say so.
"""


def get_root() -> bytes | None:
    """The trusted root for this session, or None if there is none.

    Callers must treat None as "cannot verify", never as "verified".
    """
    from storage.cache_common import APP_WARD_ROOT
    from trezor.wire import context

    root = context.cache_get(APP_WARD_ROOT)
    # An all-zero slot is an unset one, not a root: the cache hands back zeros for a
    # field that was never written.
    if not root or root == bytes(32):
        return None
    return root


def set_root(root: bytes | None) -> None:
    """Set the trusted root for this session. Debug builds only -- see `debug_set_root`."""
    from storage.cache_common import APP_WARD_ROOT
    from trezor.wire import context

    context.cache_set(APP_WARD_ROOT, root or bytes(32))
