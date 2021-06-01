# generated from all_modules.py.mako
# do not edit manually!
# flake8: noqa
# fmt: off
# isort:skip_file
from trezor.utils import halt

# this module should not be part of the build, its purpose is only to add missed Qstrings
halt("Tried to import excluded module.")

# explanation:
# uPy collects string literals and symbol names from all frozen modules, and converts
# them to qstrings for certain usages. In particular, it appears that qualified names
# of modules in sys.modules must be qstrings. However, the collection process is
# imperfect. If `apps.common.mnemonic` is always imported as `from ..common import mnemonic`,
# the string "apps.common.mnemonic" never appears in source code, is never collected,
# but then is generated and interned at runtime.
# A similar thing happens in reverse: if module `storage.cache` is always imported as
# this name, then "storage.cache" is collected but neither "storage" nor "cache" alone.
# Which is a problem, because "cache" is a symbol that is added to `storage`'s dict.
#
# We need to avoid run-time interning as much as possible, because it creates
# uncollectable garbage in the GC arena.
#
# Below, every module is listed both as import (which collects the qualified name)
# and as a symbol (which collects each individual component).
# In addition, we list the alphabet, because apparently one-character strings are always
# interned, and some operation somewhere (rendering?) is reading strings character by
# character.

from trezor import utils

all_modules
import all_modules
boot
import boot
main
import main
session
import session
usb
import usb
storage
import storage
storage.cache
import storage.cache
storage.common
import storage.common
storage.debug
import storage.debug
storage.device
import storage.device
storage.fido2
import storage.fido2
storage.recovery
import storage.recovery
storage.recovery_shares
import storage.recovery_shares
storage.resident_credentials
import storage.resident_credentials
storage.sd_salt
import storage.sd_salt
trezor
import trezor
trezor.crypto
import trezor.crypto
trezor.crypto.base32
import trezor.crypto.base32
trezor.crypto.base58
import trezor.crypto.base58
trezor.crypto.bech32
import trezor.crypto.bech32
trezor.crypto.cashaddr
import trezor.crypto.cashaddr
trezor.crypto.curve
import trezor.crypto.curve
trezor.crypto.der
import trezor.crypto.der
trezor.crypto.hashlib
import trezor.crypto.hashlib
trezor.crypto.rlp
import trezor.crypto.rlp
trezor.crypto.scripts
import trezor.crypto.scripts
trezor.crypto.slip39
import trezor.crypto.slip39
trezor.enums.AmountUnit
import trezor.enums.AmountUnit
trezor.enums.BackupType
import trezor.enums.BackupType
trezor.enums.ButtonRequestType
import trezor.enums.ButtonRequestType
trezor.enums.Capability
import trezor.enums.Capability
trezor.enums.DebugSwipeDirection
import trezor.enums.DebugSwipeDirection
trezor.enums.DecredStakingSpendType
import trezor.enums.DecredStakingSpendType
trezor.enums.FailureType
import trezor.enums.FailureType
trezor.enums.InputScriptType
import trezor.enums.InputScriptType
trezor.enums.MessageType
import trezor.enums.MessageType
trezor.enums.OutputScriptType
import trezor.enums.OutputScriptType
trezor.enums.PinMatrixRequestType
import trezor.enums.PinMatrixRequestType
trezor.enums.RecoveryDeviceType
import trezor.enums.RecoveryDeviceType
trezor.enums.RequestType
import trezor.enums.RequestType
trezor.enums.SafetyCheckLevel
import trezor.enums.SafetyCheckLevel
trezor.enums.SdProtectOperationType
import trezor.enums.SdProtectOperationType
trezor.enums.WordRequestType
import trezor.enums.WordRequestType
trezor.enums
import trezor.enums
trezor.errors
import trezor.errors
trezor.log
import trezor.log
trezor.loop
import trezor.loop
trezor.messages
import trezor.messages
trezor.pin
import trezor.pin
trezor.protobuf
import trezor.protobuf
trezor.res
import trezor.res
trezor.res.resources
import trezor.res.resources
trezor.sdcard
import trezor.sdcard
trezor.strings
import trezor.strings
trezor.ui
import trezor.ui
trezor.ui.components
import trezor.ui.components
trezor.ui.components.common
import trezor.ui.components.common
trezor.ui.components.common.confirm
import trezor.ui.components.common.confirm
trezor.ui.components.common.text
import trezor.ui.components.common.text
trezor.ui.components.tt.button
import trezor.ui.components.tt.button
trezor.ui.components.tt.checklist
import trezor.ui.components.tt.checklist
trezor.ui.components.tt.confirm
import trezor.ui.components.tt.confirm
trezor.ui.components.tt.info
import trezor.ui.components.tt.info
trezor.ui.components.tt.num_input
import trezor.ui.components.tt.num_input
trezor.ui.components.tt.passphrase
import trezor.ui.components.tt.passphrase
trezor.ui.components.tt.pin
import trezor.ui.components.tt.pin
trezor.ui.components.tt.scroll
import trezor.ui.components.tt.scroll
trezor.ui.components.tt.swipe
import trezor.ui.components.tt.swipe
trezor.ui.components.tt.text
import trezor.ui.components.tt.text
trezor.ui.components.tt.word_select
import trezor.ui.components.tt.word_select
trezor.ui.constants
import trezor.ui.constants
trezor.ui.constants.t1
import trezor.ui.constants.t1
trezor.ui.constants.tt
import trezor.ui.constants.tt
trezor.ui.container
import trezor.ui.container
trezor.ui.layouts
import trezor.ui.layouts
trezor.ui.layouts.common
import trezor.ui.layouts.common
trezor.ui.layouts.t1
import trezor.ui.layouts.t1
trezor.ui.layouts.tt
import trezor.ui.layouts.tt
trezor.ui.loader
import trezor.ui.loader
trezor.ui.popup
import trezor.ui.popup
trezor.ui.qr
import trezor.ui.qr
trezor.ui.style
import trezor.ui.style
trezor.utils
import trezor.utils
trezor.wire
import trezor.wire
trezor.wire.codec_v1
import trezor.wire.codec_v1
trezor.wire.errors
import trezor.wire.errors
trezor.workflow
import trezor.workflow
apps
import apps
apps.base
import apps.base
apps.bitcoin
import apps.bitcoin
apps.bitcoin.addresses
import apps.bitcoin.addresses
apps.bitcoin.authorization
import apps.bitcoin.authorization
apps.bitcoin.authorize_coinjoin
import apps.bitcoin.authorize_coinjoin
apps.bitcoin.common
import apps.bitcoin.common
apps.bitcoin.get_address
import apps.bitcoin.get_address
apps.bitcoin.get_ownership_id
import apps.bitcoin.get_ownership_id
apps.bitcoin.get_ownership_proof
import apps.bitcoin.get_ownership_proof
apps.bitcoin.get_public_key
import apps.bitcoin.get_public_key
apps.bitcoin.keychain
import apps.bitcoin.keychain
apps.bitcoin.multisig
import apps.bitcoin.multisig
apps.bitcoin.ownership
import apps.bitcoin.ownership
apps.bitcoin.readers
import apps.bitcoin.readers
apps.bitcoin.scripts
import apps.bitcoin.scripts
apps.bitcoin.scripts_decred
import apps.bitcoin.scripts_decred
apps.bitcoin.sign_message
import apps.bitcoin.sign_message
apps.bitcoin.sign_tx
import apps.bitcoin.sign_tx
apps.bitcoin.sign_tx.approvers
import apps.bitcoin.sign_tx.approvers
apps.bitcoin.sign_tx.bitcoin
import apps.bitcoin.sign_tx.bitcoin
apps.bitcoin.sign_tx.bitcoinlike
import apps.bitcoin.sign_tx.bitcoinlike
apps.bitcoin.sign_tx.decred
import apps.bitcoin.sign_tx.decred
apps.bitcoin.sign_tx.hash143
import apps.bitcoin.sign_tx.hash143
apps.bitcoin.sign_tx.helpers
import apps.bitcoin.sign_tx.helpers
apps.bitcoin.sign_tx.layout
import apps.bitcoin.sign_tx.layout
apps.bitcoin.sign_tx.matchcheck
import apps.bitcoin.sign_tx.matchcheck
apps.bitcoin.sign_tx.omni
import apps.bitcoin.sign_tx.omni
apps.bitcoin.sign_tx.progress
import apps.bitcoin.sign_tx.progress
apps.bitcoin.sign_tx.tx_info
import apps.bitcoin.sign_tx.tx_info
apps.bitcoin.sign_tx.tx_weight
import apps.bitcoin.sign_tx.tx_weight
apps.bitcoin.sign_tx.zcash
import apps.bitcoin.sign_tx.zcash
apps.bitcoin.verification
import apps.bitcoin.verification
apps.bitcoin.verify_message
import apps.bitcoin.verify_message
apps.bitcoin.writers
import apps.bitcoin.writers
apps.common
import apps.common
apps.common.address_type
import apps.common.address_type
apps.common.authorization
import apps.common.authorization
apps.common.cbor
import apps.common.cbor
apps.common.coininfo
import apps.common.coininfo
apps.common.coins
import apps.common.coins
apps.common.confirm
import apps.common.confirm
apps.common.keychain
import apps.common.keychain
apps.common.layout
import apps.common.layout
apps.common.passphrase
import apps.common.passphrase
apps.common.paths
import apps.common.paths
apps.common.readers
import apps.common.readers
apps.common.request_pin
import apps.common.request_pin
apps.common.safety_checks
import apps.common.safety_checks
apps.common.sdcard
import apps.common.sdcard
apps.common.seed
import apps.common.seed
apps.common.signverify
import apps.common.signverify
apps.common.writers
import apps.common.writers
apps.debug
import apps.debug
apps.debug.load_device
import apps.debug.load_device
apps.homescreen
import apps.homescreen
apps.homescreen.homescreen
import apps.homescreen.homescreen
apps.homescreen.lockscreen
import apps.homescreen.lockscreen
apps.management
import apps.management
apps.management.apply_flags
import apps.management.apply_flags
apps.management.apply_settings
import apps.management.apply_settings
apps.management.backup_device
import apps.management.backup_device
apps.management.backup_types
import apps.management.backup_types
apps.management.change_pin
import apps.management.change_pin
apps.management.change_wipe_code
import apps.management.change_wipe_code
apps.management.get_next_u2f_counter
import apps.management.get_next_u2f_counter
apps.management.recovery_device
import apps.management.recovery_device
apps.management.recovery_device.homescreen
import apps.management.recovery_device.homescreen
apps.management.recovery_device.keyboard_bip39
import apps.management.recovery_device.keyboard_bip39
apps.management.recovery_device.keyboard_slip39
import apps.management.recovery_device.keyboard_slip39
apps.management.recovery_device.layout
import apps.management.recovery_device.layout
apps.management.recovery_device.recover
import apps.management.recovery_device.recover
apps.management.recovery_device.word_validity
import apps.management.recovery_device.word_validity
apps.management.reset_device
import apps.management.reset_device
apps.management.reset_device.layout
import apps.management.reset_device.layout
apps.management.sd_protect
import apps.management.sd_protect
apps.management.set_u2f_counter
import apps.management.set_u2f_counter
apps.management.wipe_device
import apps.management.wipe_device
apps.misc
import apps.misc
apps.misc.cipher_key_value
import apps.misc.cipher_key_value
apps.misc.get_ecdh_session_key
import apps.misc.get_ecdh_session_key
apps.misc.get_entropy
import apps.misc.get_entropy
apps.misc.sign_identity
import apps.misc.sign_identity
apps.workflow_handlers
import apps.workflow_handlers

if utils.BITCOIN_ONLY:
    trezor.enums.BinanceOrderSide
    import trezor.enums.BinanceOrderSide
    trezor.enums.BinanceOrderType
    import trezor.enums.BinanceOrderType
    trezor.enums.BinanceTimeInForce
    import trezor.enums.BinanceTimeInForce
    trezor.enums.CardanoAddressType
    import trezor.enums.CardanoAddressType
    trezor.enums.CardanoCertificateType
    import trezor.enums.CardanoCertificateType
    trezor.enums.CardanoPoolRelayType
    import trezor.enums.CardanoPoolRelayType
    trezor.enums.LiskTransactionType
    import trezor.enums.LiskTransactionType
    trezor.enums.NEMImportanceTransferMode
    import trezor.enums.NEMImportanceTransferMode
    trezor.enums.NEMModificationType
    import trezor.enums.NEMModificationType
    trezor.enums.NEMMosaicLevy
    import trezor.enums.NEMMosaicLevy
    trezor.enums.NEMSupplyChangeType
    import trezor.enums.NEMSupplyChangeType
    trezor.enums.TezosBallotType
    import trezor.enums.TezosBallotType
    trezor.enums.TezosContractType
    import trezor.enums.TezosContractType
    apps.binance
    import apps.binance
    apps.binance.get_address
    import apps.binance.get_address
    apps.binance.get_public_key
    import apps.binance.get_public_key
    apps.binance.helpers
    import apps.binance.helpers
    apps.binance.layout
    import apps.binance.layout
    apps.binance.sign_tx
    import apps.binance.sign_tx
    apps.cardano
    import apps.cardano
    apps.cardano.address
    import apps.cardano.address
    apps.cardano.auxiliary_data
    import apps.cardano.auxiliary_data
    apps.cardano.byron_address
    import apps.cardano.byron_address
    apps.cardano.certificates
    import apps.cardano.certificates
    apps.cardano.get_address
    import apps.cardano.get_address
    apps.cardano.get_public_key
    import apps.cardano.get_public_key
    apps.cardano.helpers
    import apps.cardano.helpers
    apps.cardano.helpers.bech32
    import apps.cardano.helpers.bech32
    apps.cardano.helpers.network_ids
    import apps.cardano.helpers.network_ids
    apps.cardano.helpers.paths
    import apps.cardano.helpers.paths
    apps.cardano.helpers.protocol_magics
    import apps.cardano.helpers.protocol_magics
    apps.cardano.helpers.staking_use_cases
    import apps.cardano.helpers.staking_use_cases
    apps.cardano.helpers.utils
    import apps.cardano.helpers.utils
    apps.cardano.layout
    import apps.cardano.layout
    apps.cardano.seed
    import apps.cardano.seed
    apps.cardano.sign_tx
    import apps.cardano.sign_tx
    apps.common.mnemonic
    import apps.common.mnemonic
    apps.eos
    import apps.eos
    apps.eos.actions
    import apps.eos.actions
    apps.eos.actions.layout
    import apps.eos.actions.layout
    apps.eos.get_public_key
    import apps.eos.get_public_key
    apps.eos.helpers
    import apps.eos.helpers
    apps.eos.layout
    import apps.eos.layout
    apps.eos.sign_tx
    import apps.eos.sign_tx
    apps.eos.writers
    import apps.eos.writers
    apps.ethereum
    import apps.ethereum
    apps.ethereum.address
    import apps.ethereum.address
    apps.ethereum.get_address
    import apps.ethereum.get_address
    apps.ethereum.get_public_key
    import apps.ethereum.get_public_key
    apps.ethereum.keychain
    import apps.ethereum.keychain
    apps.ethereum.layout
    import apps.ethereum.layout
    apps.ethereum.networks
    import apps.ethereum.networks
    apps.ethereum.sign_message
    import apps.ethereum.sign_message
    apps.ethereum.sign_tx
    import apps.ethereum.sign_tx
    apps.ethereum.tokens
    import apps.ethereum.tokens
    apps.ethereum.verify_message
    import apps.ethereum.verify_message
    apps.lisk
    import apps.lisk
    apps.lisk.get_address
    import apps.lisk.get_address
    apps.lisk.get_public_key
    import apps.lisk.get_public_key
    apps.lisk.helpers
    import apps.lisk.helpers
    apps.lisk.layout
    import apps.lisk.layout
    apps.lisk.sign_message
    import apps.lisk.sign_message
    apps.lisk.sign_tx
    import apps.lisk.sign_tx
    apps.lisk.verify_message
    import apps.lisk.verify_message
    apps.monero
    import apps.monero
    apps.monero.diag
    import apps.monero.diag
    apps.monero.get_address
    import apps.monero.get_address
    apps.monero.get_tx_keys
    import apps.monero.get_tx_keys
    apps.monero.get_watch_only
    import apps.monero.get_watch_only
    apps.monero.key_image_sync
    import apps.monero.key_image_sync
    apps.monero.layout.common
    import apps.monero.layout.common
    apps.monero.layout.confirms
    import apps.monero.layout.confirms
    apps.monero.live_refresh
    import apps.monero.live_refresh
    apps.monero.misc
    import apps.monero.misc
    apps.monero.sign_tx
    import apps.monero.sign_tx
    apps.monero.signing
    import apps.monero.signing
    apps.monero.signing.offloading_keys
    import apps.monero.signing.offloading_keys
    apps.monero.signing.state
    import apps.monero.signing.state
    apps.monero.signing.step_01_init_transaction
    import apps.monero.signing.step_01_init_transaction
    apps.monero.signing.step_02_set_input
    import apps.monero.signing.step_02_set_input
    apps.monero.signing.step_03_inputs_permutation
    import apps.monero.signing.step_03_inputs_permutation
    apps.monero.signing.step_04_input_vini
    import apps.monero.signing.step_04_input_vini
    apps.monero.signing.step_05_all_inputs_set
    import apps.monero.signing.step_05_all_inputs_set
    apps.monero.signing.step_06_set_output
    import apps.monero.signing.step_06_set_output
    apps.monero.signing.step_07_all_outputs_set
    import apps.monero.signing.step_07_all_outputs_set
    apps.monero.signing.step_09_sign_input
    import apps.monero.signing.step_09_sign_input
    apps.monero.signing.step_10_sign_final
    import apps.monero.signing.step_10_sign_final
    apps.monero.xmr.addresses
    import apps.monero.xmr.addresses
    apps.monero.xmr.bulletproof
    import apps.monero.xmr.bulletproof
    apps.monero.xmr.credentials
    import apps.monero.xmr.credentials
    apps.monero.xmr.crypto
    import apps.monero.xmr.crypto
    apps.monero.xmr.crypto.chacha_poly
    import apps.monero.xmr.crypto.chacha_poly
    apps.monero.xmr.keccak_hasher
    import apps.monero.xmr.keccak_hasher
    apps.monero.xmr.key_image
    import apps.monero.xmr.key_image
    apps.monero.xmr.mlsag
    import apps.monero.xmr.mlsag
    apps.monero.xmr.mlsag_hasher
    import apps.monero.xmr.mlsag_hasher
    apps.monero.xmr.monero
    import apps.monero.xmr.monero
    apps.monero.xmr.networks
    import apps.monero.xmr.networks
    apps.monero.xmr.range_signatures
    import apps.monero.xmr.range_signatures
    apps.monero.xmr.serialize
    import apps.monero.xmr.serialize
    apps.monero.xmr.serialize.base_types
    import apps.monero.xmr.serialize.base_types
    apps.monero.xmr.serialize.int_serialize
    import apps.monero.xmr.serialize.int_serialize
    apps.monero.xmr.serialize.message_types
    import apps.monero.xmr.serialize.message_types
    apps.monero.xmr.serialize.readwriter
    import apps.monero.xmr.serialize.readwriter
    apps.monero.xmr.serialize_messages.base
    import apps.monero.xmr.serialize_messages.base
    apps.monero.xmr.serialize_messages.tx_ct_key
    import apps.monero.xmr.serialize_messages.tx_ct_key
    apps.monero.xmr.serialize_messages.tx_ecdh
    import apps.monero.xmr.serialize_messages.tx_ecdh
    apps.monero.xmr.serialize_messages.tx_prefix
    import apps.monero.xmr.serialize_messages.tx_prefix
    apps.monero.xmr.serialize_messages.tx_rsig_bulletproof
    import apps.monero.xmr.serialize_messages.tx_rsig_bulletproof
    apps.monero.xmr.types
    import apps.monero.xmr.types
    apps.nem
    import apps.nem
    apps.nem.get_address
    import apps.nem.get_address
    apps.nem.helpers
    import apps.nem.helpers
    apps.nem.layout
    import apps.nem.layout
    apps.nem.mosaic
    import apps.nem.mosaic
    apps.nem.mosaic.helpers
    import apps.nem.mosaic.helpers
    apps.nem.mosaic.layout
    import apps.nem.mosaic.layout
    apps.nem.mosaic.nem_mosaics
    import apps.nem.mosaic.nem_mosaics
    apps.nem.mosaic.serialize
    import apps.nem.mosaic.serialize
    apps.nem.multisig
    import apps.nem.multisig
    apps.nem.multisig.layout
    import apps.nem.multisig.layout
    apps.nem.multisig.serialize
    import apps.nem.multisig.serialize
    apps.nem.namespace
    import apps.nem.namespace
    apps.nem.namespace.layout
    import apps.nem.namespace.layout
    apps.nem.namespace.serialize
    import apps.nem.namespace.serialize
    apps.nem.sign_tx
    import apps.nem.sign_tx
    apps.nem.transfer
    import apps.nem.transfer
    apps.nem.transfer.layout
    import apps.nem.transfer.layout
    apps.nem.transfer.serialize
    import apps.nem.transfer.serialize
    apps.nem.validators
    import apps.nem.validators
    apps.nem.writers
    import apps.nem.writers
    apps.ripple
    import apps.ripple
    apps.ripple.base58_ripple
    import apps.ripple.base58_ripple
    apps.ripple.get_address
    import apps.ripple.get_address
    apps.ripple.helpers
    import apps.ripple.helpers
    apps.ripple.layout
    import apps.ripple.layout
    apps.ripple.serialize
    import apps.ripple.serialize
    apps.ripple.sign_tx
    import apps.ripple.sign_tx
    apps.stellar
    import apps.stellar
    apps.stellar.consts
    import apps.stellar.consts
    apps.stellar.get_address
    import apps.stellar.get_address
    apps.stellar.helpers
    import apps.stellar.helpers
    apps.stellar.layout
    import apps.stellar.layout
    apps.stellar.operations
    import apps.stellar.operations
    apps.stellar.operations.layout
    import apps.stellar.operations.layout
    apps.stellar.operations.serialize
    import apps.stellar.operations.serialize
    apps.stellar.sign_tx
    import apps.stellar.sign_tx
    apps.stellar.writers
    import apps.stellar.writers
    apps.tezos
    import apps.tezos
    apps.tezos.get_address
    import apps.tezos.get_address
    apps.tezos.get_public_key
    import apps.tezos.get_public_key
    apps.tezos.helpers
    import apps.tezos.helpers
    apps.tezos.layout
    import apps.tezos.layout
    apps.tezos.sign_tx
    import apps.tezos.sign_tx
    apps.webauthn
    import apps.webauthn
    apps.webauthn.add_resident_credential
    import apps.webauthn.add_resident_credential
    apps.webauthn.common
    import apps.webauthn.common
    apps.webauthn.confirm
    import apps.webauthn.confirm
    apps.webauthn.credential
    import apps.webauthn.credential
    apps.webauthn.fido2
    import apps.webauthn.fido2
    apps.webauthn.knownapps
    import apps.webauthn.knownapps
    apps.webauthn.list_resident_credentials
    import apps.webauthn.list_resident_credentials
    apps.webauthn.remove_resident_credential
    import apps.webauthn.remove_resident_credential
    apps.webauthn.resident_credentials
    import apps.webauthn.resident_credentials

# generate full alphabet
a
A
b
B
c
C
d
D
e
E
f
F
g
G
h
H
i
I
j
J
k
K
l
L
m
M
n
N
o
O
p
P
q
Q
r
R
s
S
t
T
u
U
v
V
w
W
x
X
y
Y
z
Z
