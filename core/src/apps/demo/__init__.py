from trezor import TR, loop
from trezor.ui.layouts import show_success
from trezor.ui.layouts.progress import bitcoin_progress, progress


async def demo_create_wallet() -> None:
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

    await confirm_reset_device()

    progress_layout = progress(description="Creating wallet...", title="Please wait")
    for i in range(0, 1000, 250):
        progress_layout.report(i)
        await loop.sleep(200)

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
            button=TR.instructions__continue_in_app,
            time_ms=3200,
        )


async def demo_restore_wallet() -> None:
    from trezor.enums import RecoveryType
    from trezor.ui.layouts.recovery import request_word, request_word_count

    word_count = await request_word_count(RecoveryType.NormalRecovery)
    is_slip39 = word_count in (20, 33)

    words: list[str] = [""] * word_count
    i = 0

    def all_words_entered() -> bool:
        return i >= 4

    while not all_words_entered():
        word = await request_word(
            i,
            word_count,
            is_slip39=is_slip39,
            send_button_request=False,
            prefill_word=words[i],
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
        "success_demo_recovery",
        TR.recovery__wallet_recovered,
        subheader="End of Demo",
        button=TR.instructions__continue_in_app,
        time_ms=3200,
    )


async def demo_receive_bitcoin() -> None:
    from trezor.ui.layouts import show_address

    account = "My BTC Wallet"
    # NOTE: address is invalid
    address_short = "bc1qannfxke2tfd4l7vhepehpvt05y83v3qsf6afrk"
    path = "84'/0'/0'/0/0"
    await show_address(
        address_short,
        address_qr=address_short,
        path=path,
        account=account,
        chunkify=True,
    )
    await show_success(
        "success_demo_receive",
        TR.address__confirmed,
        subheader="End of Demo",
        button=TR.instructions__continue_in_app,
        time_ms=3200,
    )


async def demo_send_bitcoin() -> None:

    from trezor.enums import ButtonRequestType as B
    from trezor.ui.layouts import confirm_output, confirm_total, show_success

    amount_str = "0.05000000 BTC"
    amount_fee_str = "0.00000555 BTC"
    amount_total_str = "0.05000555 BTC"
    source_account = "My BTC Wallet"
    source_account_path = "86'/0'/0'/0/0"
    await confirm_output(
        address="bc1q7e6qu5smalrpgqrx9k2gnf0hgjyref5p36ru2m",
        amount=amount_str,
        title="Sending to",
        hold=True,
        br_code=B.ConfirmOutput,
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

    progress_layout = bitcoin_progress(TR.progress__signing_transaction)
    for i in range(0, 1000, 350):
        progress_layout.report(i)
        await loop.sleep(400)

    # Show success screen
    await show_success(
        "success_demo_send",
        TR.send__transaction_signed,
        subheader="End of Demo",
        button=TR.instructions__continue_in_app,
        time_ms=3200,
    )
