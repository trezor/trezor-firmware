async def derive_wallet_id() -> bytes:
    """Identify the current passphrase wallet.

    Derived from the passphrase-dependent seed, so every passphrase wallet has
    its own id.
    """
    from apps.common.seed import Slip21Node, get_seed

    node = Slip21Node(await get_seed())
    node.derive_path([b"ward", b"wallet_id"])
    return node.key()
