from typing import TYPE_CHECKING
from ubinascii import hexlify

import trezorui_api
from trezor import loop, protobuf, workflow
from trezor.enums import ButtonRequestType
from trezor.wire import context, message_handler, protocol_common
from trezor.wire.context import UnexpectedMessageException
from trezor.wire.errors import ActionCancelled, SilentError
from trezor.wire.protocol_common import Context, Message
from trezor.wire.thp import ChannelState, get_enabled_pairing_methods

if TYPE_CHECKING:
    from typing import Awaitable, Container

    from trezor.enums import ThpPairingMethod
    from trezorui_api import UiResult

    from .channel import Channel
    from .cpace import Cpace

    pass

if __debug__:
    from trezor import log


class PairingContext(Context):

    def __init__(self, channel_ctx: Channel) -> None:
        super().__init__(channel_ctx.iface, channel_ctx.channel_id)
        self.channel_ctx: Channel = channel_ctx
        self.incoming_message = loop.mailbox()
        self.nfc_secret: bytes | None = None
        self.qr_code_secret: bytes | None = None
        self.code_entry_secret: bytes | None = None

        self.selected_method: ThpPairingMethod

        self.code_code_entry: int | None = None
        self.code_qr_code: bytes | None = None
        self.code_nfc: bytes | None = None
        # The 2 following attributes are important for NFC pairing
        self.nfc_secret_host: bytes | None = None
        self.handshake_hash_host: bytes | None = None

        self.cpace: Cpace
        self.host_name: str | None

    async def handle(self) -> None:
        next_message: Message | None = None

        while True:
            try:
                if next_message is None:
                    # If the previous run did not keep an unprocessed message for us,
                    # wait for a new one.
                    try:
                        message: Message = await self.incoming_message
                    except protocol_common.WireError as e:
                        if __debug__:
                            log.exception(__name__, e)
                        await self.write(message_handler.failure(e))
                        continue
                else:
                    # Process the message from previous run.
                    message = next_message
                    next_message = None

                try:
                    next_message = await handle_message(self, message)
                except Exception as exc:
                    # Log and ignore. The context handler can only exit explicitly in the
                    # following finally block.
                    if __debug__:
                        log.exception(__name__, exc)
                finally:
                    if next_message is None:

                        # Shut down the loop if there is no next message waiting.
                        return  # pylint: disable=lost-exception

            except Exception as exc:
                # Log and try again. The context handler can only exit explicitly via
                # finally block above
                if __debug__:
                    log.exception(__name__, exc)

    async def read(
        self,
        expected_types: Container[int],
        expected_type: type[protobuf.MessageType] | None = None,
    ) -> protobuf.MessageType:
        if __debug__:
            exp_type: str = str(expected_type)
            if expected_type is not None:
                exp_type = expected_type.MESSAGE_NAME
            log.debug(
                __name__,
                "Read - with expected types %s and expected type %s",
                str(expected_types),
                exp_type,
            )

        message: Message = await self.incoming_message

        if message.type not in expected_types:
            raise UnexpectedMessageException(message)

        if expected_type is None:
            expected_type = protobuf.type_for_wire(message.type)
            assert expected_type is not None

        return message_handler.wrap_protobuf_load(message.data, expected_type)

    async def write(self, msg: protobuf.MessageType) -> None:
        return await self.channel_ctx.write(msg)

    def write_force(self, msg: protobuf.MessageType) -> Awaitable[None]:
        return self.channel_ctx.write(msg, force=True)

    async def call(
        self, msg: protobuf.MessageType, expected_type: type[protobuf.MessageType]
    ) -> protobuf.MessageType:
        expected_wire_type = expected_type.MESSAGE_WIRE_TYPE
        assert expected_wire_type is not None

        await self.write(msg)
        del msg

        return await self.read((expected_wire_type,), expected_type)

    async def call_any(
        self, msg: protobuf.MessageType, *expected_types: int
    ) -> protobuf.MessageType:
        await self.write(msg)
        del msg
        return await self.read(expected_types)

    def set_selected_method(self, selected_method: ThpPairingMethod) -> None:
        if selected_method not in get_enabled_pairing_methods(self.iface):
            raise Exception("Not allowed to set this method")
        self.selected_method = selected_method

    async def show_pairing_dialog(self, device_name: str | None = None) -> None:
        from trezor.messages import ThpPairingRequestApproved
        from trezor.ui.layouts.common import interact

        if not device_name:
            action_string = f"Allow {self.host_name} to pair with this Trezor?"
        else:
            action_string = (
                f"Allow {self.host_name} on {device_name} to pair with this Trezor?"
            )

        result = await interact(
            trezorui_api.confirm_action(
                title="Before you continue", action=action_string, description=None
            ),
            br_name="thp_pairing_request",
            br_code=ButtonRequestType.Other,
        )
        if result == trezorui_api.CONFIRMED:
            await self.write(ThpPairingRequestApproved())

    async def show_connection_dialog(self, device_name: str | None = None) -> None:
        from trezor.ui.layouts.common import interact

        if not device_name:
            action_string = f"Allow {self.host_name} to pair with this Trezor?"
        else:
            action_string = (
                f"Allow {self.host_name} on {device_name} to pair with this Trezor?"
            )
        await interact(
            trezorui_api.confirm_action(
                title="Connection dialog", action=action_string, description=None
            ),
            br_name="thp_connection_request",
            br_code=ButtonRequestType.Other,
        )

    async def show_autoconnect_credential_confirmation_screen(self) -> None:
        from trezor.ui.layouts.common import interact

        await interact(
            trezorui_api.confirm_action(
                title="Autoconnect credential",
                action=f"Do you want to pair with {self.host_name} without confirmation?",
                description=None,
            ),
            br_name="autoconnect_credential_request",
            br_code=ButtonRequestType.Other,
        )

    async def show_pairing_method_screen(
        self, selected_method: ThpPairingMethod | None = None
    ) -> UiResult:
        from trezor.enums import ThpPairingMethod

        if selected_method is None:
            selected_method = self.selected_method
        if selected_method is ThpPairingMethod.CodeEntry:
            return await self._show_code_entry_screen()
        elif selected_method is ThpPairingMethod.NFC:
            return await self._show_nfc_screen()
        elif selected_method is ThpPairingMethod.QrCode:
            return await self._show_qr_code_screen()
        else:
            raise Exception("Unknown pairing method")

    async def _show_code_entry_screen(self) -> UiResult:
        from trezor.ui.layouts.common import interact

        return await interact(
            trezorui_api.show_simple(
                title="One more step",
                text=f"Enter this one-time security code on {self.host_name}\n{self._get_code_code_entry_str()}",
                button="Cancel",
            ),
            br_name=None,
        )

    async def _show_nfc_screen(self) -> UiResult:
        from trezor.ui.layouts.common import interact

        return await interact(
            trezorui_api.show_simple(
                title=None,
                text="Keep your Trezor near your phone to complete the setup.",
                button="Cancel",
            ),
            br_name=None,
        )

    async def _show_qr_code_screen(self) -> UiResult:
        from trezor.ui.layouts.common import interact

        return await interact(
            trezorui_api.show_address_details(  # noqa
                qr_title="Scan QR code to pair",
                address=self._get_code_qr_code_str(),
                case_sensitive=True,
                details_title="",
                account="",
                path="",
                xpubs=[],
            ),
            br_name=None,
            br_code=ButtonRequestType.Other,
        )

    def _get_code_code_entry_str(self) -> str:
        if self.code_code_entry is not None:
            code_str = f"{self.code_code_entry:06}"
            if __debug__:
                log.debug(__name__, "code_code_entry: %s", code_str)

            return code_str[:3] + " " + code_str[3:]
        raise Exception("Code entry string is not available")

    def _get_code_qr_code_str(self) -> str:
        if self.code_qr_code is not None:
            code_str = (hexlify(self.code_qr_code)).decode("utf-8")
            if __debug__:
                log.debug(__name__, "code_qr_code_hexlified: %s", code_str)
            return code_str
        raise Exception("QR code string is not available")


async def handle_message(
    pairing_ctx: PairingContext,
    msg: protocol_common.Message,
) -> protocol_common.Message | None:

    res_msg: protobuf.MessageType | None = None

    from apps.thp.pairing import handle_credential_phase, handle_pairing_request

    if msg.type in workflow.ALLOW_WHILE_LOCKED:
        workflow.autolock_interrupts_workflow = False

    # Here we make sure we always respond with a Failure response
    # in case of any errors.
    try:
        # Find a protobuf.MessageType subclass that describes this
        # message.  Raises if the type is not found.
        req_type = protobuf.type_for_wire(msg.type)

        # name = message_handler.get_msg_name(msg.type)
        # if name is None:
        #     req_type = protobuf.type_for_wire(msg.type)
        # else:
        #     req_type = protobuf.type_for_name(name)

        # Try to decode the message according to schema from
        # `req_type`. Raises if the message is malformed.
        req_msg = message_handler.wrap_protobuf_load(msg.data, req_type)

        # Create the handler task.
        if pairing_ctx.channel_ctx.get_channel_state() == ChannelState.TC1:
            task = handle_credential_phase(pairing_ctx, req_msg)
        else:
            task = handle_pairing_request(pairing_ctx, req_msg)

        # Run the workflow task.  Workflow can do more on-the-wire
        # communication inside, but it should eventually return a
        # response message, or raise an exception (a rather common
        # thing to do).  Exceptions are handled in the code below.
        res_msg = await workflow.spawn(context.with_context(pairing_ctx, task))

    except UnexpectedMessageException as exc:
        # Workflow was trying to read a message from the wire, and
        # something unexpected came in.  See Context.read() for
        # example, which expects some particular message and raises
        # UnexpectedMessage if another one comes in.
        # In order not to lose the message, we return it to the caller.
        # TODO:
        # We might handle only the few common cases here, like
        # Initialize and Cancel.
        return exc.msg
    except SilentError as exc:
        if __debug__:
            log.error(__name__, "SilentError: %s", exc.message)
    except BaseException as exc:
        # Either:
        # - the message had a type that has a registered handler, but does not have
        #   a protobuf class
        # - the message was not valid protobuf
        # - workflow raised some kind of an exception while running
        # - something canceled the workflow from the outside
        if __debug__:
            if isinstance(exc, ActionCancelled):
                log.debug(__name__, "cancelled: %s", exc.message)
            elif isinstance(exc, loop.TaskClosed):
                log.debug(__name__, "cancelled: loop task was closed")
            else:
                log.exception(__name__, exc)
        res_msg = message_handler.failure(exc)

    if res_msg is not None:
        # perform the write outside the big try-except block, so that usb write
        # problem bubbles up
        await pairing_ctx.write(res_msg)
    return None
