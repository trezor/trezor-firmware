async def get_creds(ctx, address_n=None, network_type=None):
    from apps.common import seed
    from apps.monero.xmr import crypto, monero
    from apps.monero.xmr.credentials import AccountCreds

    use_slip0010 = 0 not in address_n  # If path contains 0 it is not SLIP-0010

    if use_slip0010:
        curve = "ed25519"
    else:
        curve = "secp256k1"
    node = await seed.derive_node(ctx, address_n, curve)

    if use_slip0010:
        key_seed = node.private_key()
    else:
        key_seed = crypto.cn_fast_hash(node.private_key())
    spend_sec, _, view_sec, _ = monero.generate_monero_keys(key_seed)

    creds = AccountCreds.new_wallet(view_sec, spend_sec, network_type)
    return creds
