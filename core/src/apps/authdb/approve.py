from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbApprove, AuthDbApproveResponse


async def approve(msg: AuthDbApprove) -> AuthDbApproveResponse:
    """Pre-authorize an address old_value->new_value transition on the device.

    Shows address + old_value + new_value on screen (TODO: confirmation dialog).
    Returns a MAC token computed the same way AuthDbUpdateLeaf verifies it:
    HMAC(mac_key, leaf_hash(address,old_value) || leaf_hash(address,new_value)).
    A subsequent AuthDbUpdateLeaf call for this exact transition can present
    this MAC to skip the confirmation step.
    """
    from trezor.messages import AuthDbApproveResponse
    from apps.authdb import _get_wallet_id, _derive_mac_key, _compute_mac
    from apps.authdb import _mpt

    # TODO: show address + old_value + new_value confirmation dialog when UI layout is available

    wallet_id = await _get_wallet_id()
    leaf_approval_mac_key = await _derive_mac_key(b"leaf_approval")

    old_value = msg.old_value if msg.old_value else b""
    new_value = msg.new_value
    ZERO_HASH = b"\x00" * 32
    old_leaf_hash = _mpt.leaf_hash(msg.address, old_value) if old_value else ZERO_HASH
    new_leaf_hash = _mpt.leaf_hash(msg.address, new_value) if new_value else ZERO_HASH

    mac = _compute_mac(leaf_approval_mac_key, old_leaf_hash, new_leaf_hash)

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "approve: address=%s old_value=%s new_value=%s wallet_id=%s mac=%s",
            msg.address, old_value, new_value, wallet_id, mac,
        )

    return AuthDbApproveResponse(mac=mac, wallet_id=wallet_id)
