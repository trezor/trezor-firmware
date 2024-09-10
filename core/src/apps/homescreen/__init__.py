from typing import Coroutine

import storage
import storage.cache
import storage.device
from trezor import TR, config, wire
from trezor.enums import ButtonRequestType, MessageType
from trezor.ui.layouts import demo_start, show_success
from trezor.ui.layouts.homescreen import Busyscreen, Homescreen, Lockscreen

from apps.base import busy_expiry_ms, lock_device
from apps.common.authorization import is_set_any_session


async def demo_setup_wallet() -> None:
    from trezor.ui.layouts import (
        confirm_reset_device,
        prompt_backup,
        show_wallet_created_success,
    )
    from trezor.ui.layouts.reset import show_intro_backup

    from apps.management.reset_device.layout import show_and_confirm_single_share

    # Predefined demo mnemonic (20 words, not a valid wallet)
    demo_mnemonic = [
        "wealthy",
        "ability",
        "academic",
        "academic",
        "fortune",
        "above",
        "location",
        "abstract",
        "elite",
        "company",
        "access",
        "club",
        "account",
        "fantasy",
        "achieve",
        "harvest ",
        "acoustic",
        "acquire",
        "freshman",
        "act",
    ]

    # Show intro demo screen
    await demo_start("Set up a wallet")

    await confirm_reset_device(TR.reset__title_create_wallet)

    await show_wallet_created_success()

    if await prompt_backup():

        await show_intro_backup(single_share=True, num_of_words=len(demo_mnemonic))

        # Show warning
        # Show all 20 words and do wordquiz, for the DEMO the first word is always correct
        await show_and_confirm_single_share(demo_mnemonic)

        await show_success(
            "success_demo_backup",
            TR.backup__title_backup_completed,
            subheader="End of Demo",
        )


async def demo_send_bitcoin() -> None:
    from trezor import TR
    from trezor.ui.layouts import confirm_output, confirm_total, show_success

    await demo_start("Send Bitcoin")

    amount_str = "0.05000000 BTC"
    amount_fee_str = "0.00000555 BTC"
    amount_total_str = "0.05000555 BTC"
    source_account = "My BTC Wallet"
    source_account_path = "86'/0'/0'/0/0"
    await confirm_output(
        address="bc1p8denc9m4sqe9hluasrvxkkdqgkydrk5ctxre5nkk4qwdvefn0sdsc6eqxe",
        amount=amount_str,
        title="Sending to",
        hold=True,
        br_code=ButtonRequestType.ConfirmOutput,
        output_index=0,
        chunkify=True,
        source_account=source_account,
        source_account_path=source_account_path,
        cancel_text="Cancel sign",
    )

    await confirm_total(
        amount_total_str,
        amount_fee_str,
        fee_rate_amount="5 sat/vB",
        source_account=source_account,
        source_account_path=source_account_path,
    )

    # Show success screen
    await show_success(
        "success_demo_transaction", TR.send__transaction_signed, subheader="End of Demo"
    )


async def demo_recovery() -> None:
    from trezor.enums import RecoveryType
    from trezor.ui.layouts.recovery import request_word, request_word_count

    await demo_start("Recovery")

    word_count = await request_word_count(RecoveryType.NormalRecovery)
    is_slip39 = word_count in (20, 33)

    words: list[str] = [""] * word_count
    i = 0

    def all_words_entered() -> bool:
        return i >= 4

    while not all_words_entered():
        word = await request_word(
            i, word_count, is_slip39=is_slip39, prefill_word=words[i]
        )

        if not word:
            # User has decided to go back
            if i > 0:
                words[i] = ""
                i -= 1
            continue

        words[i] = word

        i += 1

    await show_success(
        "success_demo_recovery", TR.recovery__wallet_recovered, subheader="End of Demo"
    )


async def busyscreen() -> None:
    obj = Busyscreen(busy_expiry_ms())
    try:
        await obj
    finally:
        obj.__del__()


async def homescreen() -> None:
    from trezor import TR
    from trezorui2 import CONFIRMED

    if storage.device.is_initialized():
        label = storage.device.get_label()
    else:
        label = None

    # Set default PIN for DEMO branch
    if not config.has_pin():
        config.change_pin("", "1234", None, None)
        # lock_device()

    # TODO: add notification that translations are out of date

    notification: str | None = None
    notification_is_error: bool = False
    if is_set_any_session(MessageType.AuthorizeCoinJoin):
        notification = TR.homescreen__title_coinjoin_authorized
    elif storage.device.is_initialized() and storage.device.no_backup():
        notification = TR.homescreen__title_seedless
        notification_is_error = True
    elif storage.device.is_initialized() and storage.device.unfinished_backup():
        notification = TR.homescreen__title_backup_failed
        notification_is_error = True
    elif storage.device.is_initialized() and storage.device.needs_backup():
        notification = TR.homescreen__title_backup_needed
    elif storage.device.is_initialized() and not config.has_pin():
        notification = TR.homescreen__title_pin_not_set
    elif storage.device.get_experimental_features():
        notification = TR.homescreen__title_experimental_mode

    obj = Homescreen(
        label=label,
        notification=notification,
        notification_is_error=notification_is_error,
        hold_to_lock=config.has_pin(),
    )
    try:
        res = await obj
        if isinstance(res, tuple) and res[0] is CONFIRMED:
            # res is (CONFIRMED, int), something was chosen from the menu
            choice = res[1]
            if choice == 0:
                from trezor.ui.layouts import tutorial

                await tutorial()
            elif choice == 1:
                await demo_setup_wallet()
            elif choice == 2:
                await demo_send_bitcoin()
            elif choice == 3:
                await demo_recovery()
        else:
            lock_device()
    finally:
        obj.__del__()


async def _lockscreen(screensaver: bool = False) -> None:
    from apps.base import unlock_device
    from apps.common.request_pin import can_lock_device

    # Only show the lockscreen UI if the device can in fact be locked, or if it is
    # and OLED device (in which case the lockscreen is a screensaver).
    if can_lock_device() or screensaver:
        obj = Lockscreen(
            label=storage.device.get_label(),
            coinjoin_authorized=is_set_any_session(MessageType.AuthorizeCoinJoin),
        )
        try:
            await obj
        finally:
            obj.__del__()
    # Otherwise proceed directly to unlock() call. If the device is already unlocked,
    # it should be a no-op storage-wise, but it resets the internal configuration
    # to an unlocked state.
    try:
        await unlock_device()
    except wire.PinCancelled:
        pass


def lockscreen() -> Coroutine[None, None, None]:
    return _lockscreen()


def screensaver() -> Coroutine[None, None, None]:
    return _lockscreen(screensaver=True)
