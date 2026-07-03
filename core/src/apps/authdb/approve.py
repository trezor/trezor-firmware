from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthDbApprove, AuthDbApproveResponse


async def approve(msg: AuthDbApprove) -> AuthDbApproveResponse:
    """Pre-authorize an (address, value) pair on the device.

    Shows address + value on screen (TODO: confirmation dialog).
    Returns a MAC token = HMAC-SHA256(slip21_key, address‖value).
    Subsequent update_leaf calls that present this MAC skip the confirmation step.
    """
    from trezor.messages import AuthDbApproveResponse
    from apps.authdb import _get_wallet_id, _derive_mac_key, _compute_mac

    # TODO: show address + value confirmation dialog when UI layout is available

    wallet_id = await _get_wallet_id()
    mac_key = await _derive_mac_key()
    mac = _compute_mac(mac_key, msg.address, msg.value)

    if __debug__:
        from trezor import log
        log.debug(
            __name__,
            "approve: address=%s value=%s wallet_id=%s mac=%s",
            msg.address, msg.value, wallet_id, mac,
        )

    return AuthDbApproveResponse(mac=mac, wallet_id=wallet_id)
