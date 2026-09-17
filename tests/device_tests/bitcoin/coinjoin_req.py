# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

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
