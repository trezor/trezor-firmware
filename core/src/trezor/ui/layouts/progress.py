import trezorui_api
from trezor import TR, config, ui, utils


def _storage_message_to_str(message: config.StorageMessage | None) -> str | None:
    from trezor import TR

    if message is None:
        return None

    if message == config.StorageMessage.NO_MSG:
        return ""
    if message == config.StorageMessage.VERIFYING_PIN_MSG:
        return TR.storage_msg__verifying_pin
    if message == config.StorageMessage.PROCESSING_MSG:
        return TR.storage_msg__processing
    if message == config.StorageMessage.STARTING_MSG:
        return TR.storage_msg__starting
    if message == config.StorageMessage.WRONG_PIN_MSG:
        return TR.storage_msg__wrong_pin
    raise RuntimeError  # unknown message


def progress(
    description: str | None = None,
    title: str | None = None,
    indeterminate: bool = False,
) -> ui.ProgressLayout:
    if description is None:
        description = TR.progress__please_wait  # def_arg

    return ui.ProgressLayout(
        layout=trezorui_api.show_progress(
            description=description,
            title=title,
            indeterminate=indeterminate,
        )
    )


def bitcoin_progress(message: str) -> ui.ProgressLayout:
    return progress(message)


def coinjoin_progress(message: str) -> ui.ProgressLayout:
    return ui.ProgressLayout(
        layout=trezorui_api.show_progress_coinjoin(title=message, indeterminate=False)
    )


def pin_progress(title: config.StorageMessage, description: str) -> ui.ProgressLayout:
    return progress(description=description, title=_storage_message_to_str(title))


if not utils.BITCOIN_ONLY:

    def monero_keyimage_sync_progress() -> ui.ProgressLayout:
        return progress(TR.progress__syncing)

    def monero_live_refresh_progress() -> ui.ProgressLayout:
        return progress(TR.progress__refreshing, indeterminate=True)

    def monero_transaction_progress_inner() -> ui.ProgressLayout:
        return progress(TR.progress__signing_transaction)
