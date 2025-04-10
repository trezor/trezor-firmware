from trezorlib import messages


def make_coinjoin_request(
    coordinator_name,
    inputs,
    input_script_pubkeys,
    outputs,
    output_script_pubkeys,
    no_fee_indices,
    fee_rate=500_000,  # 0.5 %
    no_fee_threshold=1_000_000,
    min_registrable_amount=5_000,
):
    # Process inputs.
    for i, txi in enumerate(inputs):
        # Set no_fee flag in coinjoin_flags.
        txi.coinjoin_flags |= (i in no_fee_indices) << 1

    return messages.CoinJoinRequest(
        fee_rate=fee_rate,
        no_fee_threshold=no_fee_threshold,
        min_registrable_amount=min_registrable_amount,
        mask_public_key=b"",
        signature=b"",
    )
