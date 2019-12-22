from trezor import wire
from trezor import wire, ui
from trezor.ui.text import Text
from trezor.ui.scroll import Paginated

from trezor.messages import MessageType, ButtonRequestType
from trezor.messages.NEM2EncryptMessage import NEM2EncryptMessage
from trezor.messages.NEM2EncryptedMessage import NEM2EncryptedMessage
from trezor.crypto import random, aes
from ubinascii import unhexlify, hexlify

from apps.common import HARDENED
from apps.common.paths import validate_path

from apps.nem2.helpers import NEM2_SALT_SIZE, AES_BLOCK_SIZE, derive_shared_key

from apps.nem2.helpers import validate_nem2_path, NEM2_HASH_ALG

from apps.nem2.validators import validate_encrypt_message

from apps.common.confirm import require_hold_to_confirm
from apps.common.layout import split_address

from apps.nem2 import CURVE

async def encrypt_message(ctx, msg: NEM2EncryptMessage, keychain) -> NEM2EncryptedMessage:
  validate_encrypt_message(msg)

  await validate_path(
      ctx,
      validate_nem2_path,
      keychain,
      msg.address_n,
      CURVE,
  )

  properties = []

  t = Text("Encrypt Message", ui.ICON_SEND, new_lines=False)
  t.bold("For Public Key:")
  t.mono(*split_address(msg.recipient_public_key.upper()))
  properties.append(t)

  t = Text("Encrypt Message", ui.ICON_SEND, new_lines=False)
  t.bold("Message:")
  t.br()
  t.normal(msg.payload)
  properties.append(t)


  paginated = Paginated(properties)
  await require_hold_to_confirm(ctx, paginated, ButtonRequestType.ConfirmOutput)

  node = keychain.derive(msg.address_n, CURVE)

  salt = random.bytes(NEM2_SALT_SIZE)
  iv = random.bytes(AES_BLOCK_SIZE)

  # 1. generate a shared key between sender private key and recipient public key
  shared_key = derive_shared_key(salt, node.private_key(), unhexlify(msg.recipient_public_key))

  # 2. encrypt the message payload using AES
  ctx = aes(aes.CBC, shared_key, iv)
  enc = ctx.encrypt(bytes(msg.payload, "ascii"))

  encrypted_payload = salt + iv + enc

  return NEM2EncryptedMessage(
    payload=encrypted_payload
  )