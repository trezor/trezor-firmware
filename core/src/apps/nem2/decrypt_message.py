from trezor import wire, ui
from trezor.ui.text import Text
from trezor.ui.scroll import Paginated

from trezor.messages import MessageType, ButtonRequestType
from trezor.messages.NEM2DecryptMessage import NEM2DecryptMessage
from trezor.messages.NEM2DecryptedMessage import NEM2DecryptedMessage
from trezor.crypto import random, aes
from ubinascii import unhexlify, hexlify

from apps.common import HARDENED
from apps.common.paths import validate_path


from apps.nem2.helpers import NEM2_SALT_SIZE, AES_BLOCK_SIZE, derive_shared_key

from apps.nem2.helpers import validate_nem2_path, NEM2_HASH_ALG

from apps.nem2.validators import validate_decrypt_message

from apps.common.confirm import require_hold_to_confirm
from apps.common.layout import split_address

from apps.nem2 import CURVE

async def decrypt_message(ctx, msg: NEM2DecryptMessage, keychain) -> NEM2DecryptedMessage:
  validate_decrypt_message(msg)

  await validate_path(
      ctx,
      validate_nem2_path,
      keychain,
      msg.address_n,
      CURVE,
  )

  properties = []

  t = Text("Decrypt Message", ui.ICON_SEND, new_lines=False)
  t.bold("From Public Key:")
  t.mono(*split_address(msg.sender_public_key.upper()))
  properties.append(t)

  t = Text("Decrypt Message", ui.ICON_SEND, new_lines=False)
  t.bold("Encrypted Message:")
  t.mono(*split_address(msg.payload[:20] + "..." + msg.payload[-20:]))
  properties.append(t)


  paginated = Paginated(properties)
  await require_hold_to_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)

  node = keychain.derive(msg.address_n, CURVE)

  payload_bytes = unhexlify(msg.payload)

  salt = payload_bytes[:32]
  iv = payload_bytes[32:48]
  message = payload_bytes[48:]

  # 1. generate a shared key between sender public key and recipient private key
  shared_key = derive_shared_key(salt, node.private_key(), unhexlify(msg.sender_public_key))

  # 2. decrypt the message payload using AES
  ctx = aes(aes.CBC, shared_key, iv)
  decrypted_payload = ctx.decrypt(message)

  return NEM2DecryptedMessage(
    payload=decrypted_payload
  )