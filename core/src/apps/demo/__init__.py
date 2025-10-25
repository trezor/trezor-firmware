from micropython import const
from typing import TYPE_CHECKING

from trezor import TR, loop
from trezor.ui.layouts import show_success
from trezor.ui.layouts.progress import bitcoin_progress, progress

if TYPE_CHECKING:
    from trezor.ui import ProgressLayout


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

    await simulate_progress(
        layout=progress(description="Creating demo wallet...", title="Please wait"),
        step=250,
        delay_ms=200,
    )

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
    # NOTE: address checksum is invalid
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
    from trezor.ui.layouts import confirm_output, confirm_total

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

    await simulate_signature()


async def demo_swap_assets() -> None:

    from trezor.ui.layouts import confirm_payment_request

    DEMO_TRADE = (
        "- 9.84 ETH",
        "+ 200 SOL",
        "CqPFGxxzrE2bgLGC98x9rYix7Nq17mh8L7pWseJt3c9N",
        None,
        None,
    )

    await confirm_payment_request(
        recipient_name="Trezor.io",
        recipient="0x1ec5C1854e3E9F1674c34D6C2Be1bf13DFc0Fd8F",
        texts=[],
        refunds=[],
        trades=[DEMO_TRADE],
        account_items=[
            ("Wallet", "Standard", False),
            ("Account", "ETH", False),
            ("Derivation path", "m/44'/60'/0'/0/0", False),
        ],
        transaction_fee="0.01214 ETH",
        fee_info_items=[("Fee rate", "1 Gwei", False)],
        token_address=None,
    )

    await simulate_signature()


async def demo_approve_contract() -> None:

    from trezor.ui.layouts import confirm_ethereum_approve

    await confirm_ethereum_approve(
        recipient_addr="0xe592427a0aece92de3edee1f18e0157c05861564",
        recipient_str="Uniswap v3",
        is_unknown_token=False,
        token_address="",
        token_symbol="USDT",
        is_unknown_network=False,
        chain_id="",
        network_name="Ethereum",
        is_revoke=False,
        total_amount="32.4321 USDT",
        account="ETH",
        account_path="m/44'/60'/0'/0/0",
        maximum_fee="0.0000721 USDT",
        fee_info_items=[
            ("Gas limit", "21000 units", True),
            ("Max fee per gas", "3.28 Gwei", False),
            ("Gas limit", "1.70 Gwei", None),
        ],
        chunkify=True,
    )

    await simulate_signature()


_PROGRESS_END = const(1000)


async def simulate_progress(layout: ProgressLayout, step: int, delay_ms: int) -> None:
    for i in range(0, _PROGRESS_END, step):
        layout.report(i)
        await loop.sleep(delay_ms)

    layout.report(_PROGRESS_END)
    await loop.sleep(delay_ms)


async def simulate_signature() -> None:
    await simulate_progress(
        layout=bitcoin_progress(TR.progress__signing_transaction),
        step=350,
        delay_ms=400,
    )

    # Show success screen
    await show_success(
        "success_demo_send",
        TR.send__transaction_signed,
        subheader="End of Demo",
        button=TR.instructions__continue_in_app,
        time_ms=3200,
    )
