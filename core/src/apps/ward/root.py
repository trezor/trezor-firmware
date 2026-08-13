"""The trie root the device verifies proofs against.

A proof only means something when checked against a root the host did not choose. This
holds that root, in the SESSION CACHE.

The device DERIVES it: every confirmed write recomputes the root from a state the host had
to prove (see `trie.compute_new_root`), so this is a value the device computed, never one
it was handed. There is deliberately no way for the host to set it -- an earlier
`WARDDebugSetRoot` existed only while writes could not derive one, and was removed rather
than left as a back door into the one number the whole scheme rests on.

Two reasons it must live there rather than in a module global, and the first is fatal:

  - Module state does not survive a workflow. `trezor.wire` wraps every request in
    `utils.unimport_begin()` / `unimport_end()`, which deletes from `sys.modules` every
    module the workflow imported. A root stashed in a module attribute is gone by the
    time the next request arrives, so it would silently read back as "no root" -- i.e.
    as "cannot verify", which fails open in the sense that nothing gets checked.
  - The session is also the right LIFETIME. K_path is passphrase-dependent, so each
    hidden wallet has its own trie and therefore its own root; a root shared across
    sessions would belong to whichever wallet happened to set it last.

FIXME(ward, TRANSITIONAL): the root does not survive a restart, so a device that reboots
forgets its tree and verifies nothing again until the next write. Persisting it needs a
per-wallet slot in flash -- the trie is passphrase-dependent, so one device holds one root
PER hidden wallet -- and a counter, because roots repeat whenever contents repeat and so
cannot identify a state by themselves. That is the next step.

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
    """Record the root the device just derived. Callers must have computed it themselves."""
    from storage.cache_common import APP_WARD_ROOT
    from trezor.wire import context

    context.cache_set(APP_WARD_ROOT, root or bytes(32))
