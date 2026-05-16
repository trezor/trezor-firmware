def require_initialized() -> None:
    import storage.device as storage_device
    from trezor import wire

    if not storage_device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")
