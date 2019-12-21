from trezor import wire
from trezor.messages import MessageType
from trezor.messages.NEM2DecryptMessage import NEM2DecryptMessage
from trezor.messages.NEM2DecryptedMessage import NEM2DecryptedMessage
from trezor.crypto import random, aes
from trezor.crypto.curve import ed25519
from ubinascii import unhexlify, hexlify

from apps.common import HARDENED
from apps.common.paths import validate_path

from apps.nem2.helpers import NEM2_SALT_SIZE, AES_BLOCK_SIZE, derive_shared_key

from apps.nem2.helpers import validate_nem2_path, NEM2_HASH_ALG

from apps.nem2.validators import validate_decrypt_message

CURVE = "ed25519-keccak"

async def decrypt_message(ctx, msg: NEM2DecryptMessage, keychain) -> NEM2DecryptedMessage:
  validate_decrypt_message(msg)

  await validate_path(
      ctx,
      validate_nem2_path,
      keychain,
      msg.address_n,
      CURVE,
  )

  node = keychain.derive(msg.address_n, CURVE)

  salt = random.bytes(NEM2_SALT_SIZE)
  iv = random.bytes(AES_BLOCK_SIZE)

  # 1. generate a shared key between sender private key and recipient public key
  shared_key = derive_shared_key(salt, node.private_key(), msg.recipient_public_key)
  # 2. encrypt the message payload using AES
  cipher = aes(aes.CBC, shared_key)

  encrypted_payload = iv + salt + cipher.encrypt(unhexlify(msg.payload))

  return NEM2DecryptedMessage(
    payload=encrypted_payload.decode("utf-8")
  )