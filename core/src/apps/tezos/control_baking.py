from trezor import config, wire, workflow
from trezor.messages.Failure import Failure
from trezor.messages.Success import Success
from trezor.messages import MessageType

from apps.tezos import ns, helpers, layout
from apps.tezos.baking_homescreen import baking_homescreen

# list of messages used in Tezos baking
tezos_baking_allowed_messages = [
    MessageType.Initialize,
    MessageType.TezosGetAddress,
    MessageType.TezosGetPublicKey,
]


async def control_baking(ctx, msg):
    if not config.has_pin():
        return Failure()

    await layout.require_confirm_baking(ctx)

    # remove unused handlers
    wire.clear_handlers(tezos_baking_allowed_messages)

    # register the baker singing message
    wire.add(MessageType.TezosSignBakerOp, "apps.tezos", "sign_baker_op", ns)

    # start a new homescreen
    workflow.closedefault()
    workflow.startdefault(baking_homescreen)

    return Success(message="Baking mode activated")
