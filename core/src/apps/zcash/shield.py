from trezor.messages import (
	ZcashPushAction,
	ZcashShieldedAction,
)
from trezor.enums import ButtonRequestType
from trezor.ui.layouts import (
    confirm_action,
    confirm_blob,
    confirm_metadata,
    confirm_output,
)
from trezor.wire import ProcessError
from trezor.crypto import zcash
from . import zip32
from .address import parse_unified, ORCHARD

if False:
	from trezor.wire import Context

def _format_amount(value):
    return "%s ZEC" % strings.format_amount(value, 12) #12 ???

async def shield(ctx: Context, msg: ZcashPushAction) -> ZcashShieldedAction:
	action_info = dict()
	if msg.spend_info != None:
		zip32.verify_path(msg.z_address_n)
		master = await zip32.get_master(ctx)
		sk = master.derive(msg.z_address_n).spending_key()
		action_info["spend_info"] = {
			"sk": sk,
			"value": msg.value,
			"nullifier": msg.nullifier,
			"rseed": msg.rseed
		}

	if msg.recipient_info != None:
		raw_address = parse_unified(msg.address).get(ORCHARD)
		if raw_address == None:
			raise ProcessError("Orchard receiver not found.")

		await confirm_output(
	        ctx,
	        address=msg.address[..26],
	        amount=_format_amount(msg.amount),
	        font_amount=ui.BOLD,
	        br_code=ButtonRequestType.SignTx,
    	)

		action_info["recipient_info"] = {
			"ovk_flag": msg.ovk_flag,
			"address": raw_address
			"value": msg.amount,
			"memo": msg.memo,
		}

	shielded = zcash.shield(action_info)

	return ZcashShieldedAction(**shielded)