# pylint: disable=E0602

CCFLAGS_MOD = ''
CPPPATH_MOD = []
CPPDEFINES_MOD = []
SOURCE_MOD = []

# modtrezorconfig
SOURCE_MOD += [
    'embed/extmod/modtrezorconfig/modtrezorconfig.c',
    'embed/extmod/modtrezorconfig/norcow.c',
]

# modtrezorcrypto
CCFLAGS_MOD += '-Wno-sequence-point '
CPPPATH_MOD += [
    'embed/extmod/modtrezorcrypto/trezor-crypto',
    'embed/extmod/modtrezorcrypto/trezor-crypto/aes',
    'embed/extmod/modtrezorcrypto/trezor-crypto/ed25519-donna',
]
CPPDEFINES_MOD += [
    'AES_128',
    'AES_192',
    'USE_KECCAK',
]
SOURCE_MOD += [
    'embed/extmod/modtrezorcrypto/modtrezorcrypto.c',
    'embed/extmod/modtrezorcrypto/rand.c',
    'embed/extmod/modtrezorcrypto/ssss.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/address.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/aes/aescrypt.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/aes/aeskey.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/aes/aes_modes.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/aes/aestab.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/base58.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/bignum.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/bip32.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/bip39.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/blake2b.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/blake2s.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/curves.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/ecdsa.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/ed25519-donna/ed25519.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/hmac.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/nist256p1.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/pbkdf2.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/ripemd160.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/secp256k1.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/sha2.c',
    'embed/extmod/modtrezorcrypto/trezor-crypto/sha3.c',
]

# modtrezorio
SOURCE_MOD += [
    'embed/extmod/modtrezorio/modtrezorio.c',
]

# modtrezormsg
SOURCE_MOD += [
    'embed/extmod/modtrezormsg/modtrezormsg.c',
]

# modtrezorui
CPPDEFINES_MOD += [('QR_MAX_VERSION', '0')]
SOURCE_MOD += [
    'embed/extmod/modtrezorui/display.c',
    'embed/extmod/modtrezorui/inflate.c',
    'embed/extmod/modtrezorui/font_bitmap.c',
    'embed/extmod/modtrezorui/font_roboto_bold_20.c',
    'embed/extmod/modtrezorui/font_roboto_regular_20.c',
    'embed/extmod/modtrezorui/font_robotomono_regular_20.c',
    'embed/extmod/modtrezorui/modtrezorui.c',
    'embed/extmod/modtrezorui/trezor-qrenc/qr_encode.c',
]

# modtrezorutils
SOURCE_MOD += [
    'embed/extmod/modtrezorutils/modtrezorutils.c',
]

# modutime
SOURCE_MOD += [
    'embed/firmware/modutime.c',
]

SOURCE_MICROPYTHON = [
    'vendor/micropython/extmod/modubinascii.c',
    'vendor/micropython/extmod/moductypes.c',
    'vendor/micropython/extmod/moduheapq.c',
    'vendor/micropython/extmod/modutimeq.c',
    'vendor/micropython/extmod/moduzlib.c',
    'vendor/micropython/extmod/utime_mphal.c',
    'vendor/micropython/lib/embed/abort_.c',
    'vendor/micropython/lib/libc/string0.c',
    'vendor/micropython/lib/libm/acoshf.c',
    'vendor/micropython/lib/libm/asinfacosf.c',
    'vendor/micropython/lib/libm/asinhf.c',
    'vendor/micropython/lib/libm/atan2f.c',
    'vendor/micropython/lib/libm/atanf.c',
    'vendor/micropython/lib/libm/atanhf.c',
    'vendor/micropython/lib/libm/ef_rem_pio2.c',
    'vendor/micropython/lib/libm/erf_lgamma.c',
    'vendor/micropython/lib/libm/fmodf.c',
    'vendor/micropython/lib/libm/kf_cos.c',
    'vendor/micropython/lib/libm/kf_rem_pio2.c',
    'vendor/micropython/lib/libm/kf_sin.c',
    'vendor/micropython/lib/libm/kf_tan.c',
    'vendor/micropython/lib/libm/log1pf.c',
    'vendor/micropython/lib/libm/math.c',
    'vendor/micropython/lib/libm/nearbyintf.c',
    'vendor/micropython/lib/libm/roundf.c',
    'vendor/micropython/lib/libm/sf_cos.c',
    'vendor/micropython/lib/libm/sf_erf.c',
    'vendor/micropython/lib/libm/sf_frexp.c',
    'vendor/micropython/lib/libm/sf_ldexp.c',
    'vendor/micropython/lib/libm/sf_modf.c',
    'vendor/micropython/lib/libm/sf_sin.c',
    'vendor/micropython/lib/libm/sf_tan.c',
    'vendor/micropython/lib/libm/thumb_vfp_sqrtf.c',
    'vendor/micropython/lib/libm/wf_lgamma.c',
    'vendor/micropython/lib/libm/wf_tgamma.c',
    'vendor/micropython/lib/mp-readline/readline.c',
    'vendor/micropython/lib/utils/interrupt_char.c',
    'vendor/micropython/lib/utils/printf.c',
    'vendor/micropython/lib/utils/pyexec.c',
    'vendor/micropython/lib/utils/stdout_helpers.c',
    'vendor/micropython/py/argcheck.c',
    'vendor/micropython/py/asmarm.c',
    'vendor/micropython/py/asmbase.c',
    'vendor/micropython/py/asmthumb.c',
    'vendor/micropython/py/asmx64.c',
    'vendor/micropython/py/asmx86.c',
    'vendor/micropython/py/asmxtensa.c',
    'vendor/micropython/py/bc.c',
    'vendor/micropython/py/binary.c',
    'vendor/micropython/py/builtinevex.c',
    'vendor/micropython/py/builtinhelp.c',
    'vendor/micropython/py/builtinimport.c',
    'vendor/micropython/py/compile.c',
    'vendor/micropython/py/emitbc.c',
    'vendor/micropython/py/emitcommon.c',
    'vendor/micropython/py/emitglue.c',
    'vendor/micropython/py/emitinlinethumb.c',
    'vendor/micropython/py/emitinlinextensa.c',
    'vendor/micropython/py/formatfloat.c',
    'vendor/micropython/py/frozenmod.c',
    'vendor/micropython/py/gc.c',
    'vendor/micropython/py/lexer.c',
    'vendor/micropython/py/malloc.c',
    'vendor/micropython/py/map.c',
    'vendor/micropython/py/modarray.c',
    'vendor/micropython/py/modbuiltins.c',
    'vendor/micropython/py/modcmath.c',
    'vendor/micropython/py/modcollections.c',
    'vendor/micropython/py/modgc.c',
    'vendor/micropython/py/modio.c',
    'vendor/micropython/py/modmath.c',
    'vendor/micropython/py/modmicropython.c',
    'vendor/micropython/py/modstruct.c',
    'vendor/micropython/py/modsys.c',
    'vendor/micropython/py/modthread.c',
    'vendor/micropython/py/moduerrno.c',
    'vendor/micropython/py/mpprint.c',
    'vendor/micropython/py/mpstate.c',
    'vendor/micropython/py/mpz.c',
    'vendor/micropython/py/nativeglue.c',
    'vendor/micropython/py/nlrsetjmp.c',
    'vendor/micropython/py/nlrthumb.c',
    'vendor/micropython/py/nlrx64.c',
    'vendor/micropython/py/nlrx86.c',
    'vendor/micropython/py/nlrxtensa.c',
    'vendor/micropython/py/obj.c',
    'vendor/micropython/py/objarray.c',
    'vendor/micropython/py/objattrtuple.c',
    'vendor/micropython/py/objbool.c',
    'vendor/micropython/py/objboundmeth.c',
    'vendor/micropython/py/objcell.c',
    'vendor/micropython/py/objclosure.c',
    'vendor/micropython/py/objcomplex.c',
    'vendor/micropython/py/objdict.c',
    'vendor/micropython/py/objenumerate.c',
    'vendor/micropython/py/objexcept.c',
    'vendor/micropython/py/objfilter.c',
    'vendor/micropython/py/objfloat.c',
    'vendor/micropython/py/objfun.c',
    'vendor/micropython/py/objgenerator.c',
    'vendor/micropython/py/objgetitemiter.c',
    'vendor/micropython/py/objint_longlong.c',
    'vendor/micropython/py/objint_mpz.c',
    'vendor/micropython/py/objint.c',
    'vendor/micropython/py/objlist.c',
    'vendor/micropython/py/objmap.c',
    'vendor/micropython/py/objmodule.c',
    'vendor/micropython/py/objnamedtuple.c',
    'vendor/micropython/py/objnone.c',
    'vendor/micropython/py/objobject.c',
    'vendor/micropython/py/objpolyiter.c',
    'vendor/micropython/py/objproperty.c',
    'vendor/micropython/py/objrange.c',
    'vendor/micropython/py/objreversed.c',
    'vendor/micropython/py/objset.c',
    'vendor/micropython/py/objsingleton.c',
    'vendor/micropython/py/objslice.c',
    'vendor/micropython/py/objstr.c',
    'vendor/micropython/py/objstringio.c',
    'vendor/micropython/py/objstrunicode.c',
    'vendor/micropython/py/objtuple.c',
    'vendor/micropython/py/objtype.c',
    'vendor/micropython/py/objzip.c',
    'vendor/micropython/py/opmethods.c',
    'vendor/micropython/py/parse.c',
    'vendor/micropython/py/parsenum.c',
    'vendor/micropython/py/parsenumbase.c',
    'vendor/micropython/py/persistentcode.c',
    'vendor/micropython/py/qstr.c',
    'vendor/micropython/py/reader.c',
    'vendor/micropython/py/repl.c',
    'vendor/micropython/py/runtime_utils.c',
    'vendor/micropython/py/runtime.c',
    'vendor/micropython/py/scope.c',
    'vendor/micropython/py/sequence.c',
    'vendor/micropython/py/showbc.c',
    'vendor/micropython/py/smallint.c',
    'vendor/micropython/py/stackctrl.c',
    'vendor/micropython/py/stream.c',
    'vendor/micropython/py/unicode.c',
    'vendor/micropython/py/vm.c',
    'vendor/micropython/py/vstr.c',
    'vendor/micropython/py/warning.c',
    'vendor/micropython/stmhal/gccollect.c',
    'vendor/micropython/stmhal/gchelper.s',
    'vendor/micropython/stmhal/pendsv.c',
    'vendor/micropython/stmhal/startup_stm32.S',
    'vendor/micropython/stmhal/systick.c',
]

SOURCE_STMHAL = [
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_adc_ex.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_adc.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_can.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_cortex.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_dac_ex.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_dac.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_dma.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_flash_ex.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_flash.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_gpio.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_i2c.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_pcd_ex.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_pcd.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_pwr_ex.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_pwr.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_rcc_ex.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_rcc.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_rng.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_rtc_ex.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_rtc.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_sd.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_spi.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_tim_ex.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_tim.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal_uart.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_hal.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_ll_sdmmc.c',
    'vendor/micropython/stmhal/hal/f4/src/stm32f4xx_ll_usb.c',
]

SOURCE_FIRMWARE = [
    'embed/firmware/main.c',
    'embed/firmware/mphalport.c',
]

SOURCE_TREZORHAL = [
    'embed/trezorhal/common.c',
    'embed/trezorhal/flash.c',
    'embed/trezorhal/mini_printf.c',
    'embed/trezorhal/rng.c',
    'embed/trezorhal/sdcard.c',
    'embed/trezorhal/stm32_it.c',
    'embed/trezorhal/stm32_system.c',
    'embed/trezorhal/touch.c',
    'embed/trezorhal/usb.c',
    'embed/trezorhal/usbd_conf.c',
    'embed/trezorhal/usbd_core.c',
    'embed/trezorhal/usbd_ctlreq.c',
    'embed/trezorhal/usbd_ioreq.c',
    'embed/trezorhal/hal/stm32f4xx_hal_sram.c',
    'embed/trezorhal/hal/stm32f4xx_ll_fsmc.c',
]

SOURCE_QSTR = SOURCE_MOD + SOURCE_MICROPYTHON

SOURCE_PY = [
    'src/apps/__init__.py',
    'src/apps/common/__init__.py',
    'src/apps/common/address_type.py',
    'src/apps/common/cache.py',
    'src/apps/common/coins.py',
    'src/apps/common/confirm.py',
    'src/apps/common/request_passphrase.py',
    'src/apps/common/request_pin.py',
    'src/apps/common/seed.py',
    'src/apps/common/signverify.py',
    'src/apps/common/storage.py',
    'src/apps/debug/__init__.py',
    'src/apps/ethereum/__init__.py',
    'src/apps/ethereum/ethereum_get_address.py',
    'src/apps/fido_u2f/__init__.py',
    'src/apps/fido_u2f/knownapps.py',
    'src/apps/homescreen/__init__.py',
    'src/apps/homescreen/homescreen.py',
    'src/apps/management/__init__.py',
    'src/apps/management/apply_settings.py',
    'src/apps/management/change_pin.py',
    'src/apps/management/load_device.py',
    'src/apps/management/recovery_device.py',
    'src/apps/management/reset_device.py',
    'src/apps/management/wipe_device.py',
    'src/apps/wallet/__init__.py',
    'src/apps/wallet/cipher_key_value.py',
    'src/apps/wallet/get_address.py',
    'src/apps/wallet/get_entropy.py',
    'src/apps/wallet/get_public_key.py',
    'src/apps/wallet/sign_identity.py',
    'src/apps/wallet/sign_message.py',
    'src/apps/wallet/sign_tx/__init__.py',
    'src/apps/wallet/sign_tx/layout.py',
    'src/apps/wallet/sign_tx/signing.py',
    'src/apps/wallet/verify_message.py',
    'src/lib/__init__.py',
    'src/lib/protobuf.py',
    'src/lib/typing.py',
    'src/lib/unittest.py',
    'src/main.py',
    'src/trezor/__init__.py',
    'src/trezor/crypto/__init__.py',
    'src/trezor/crypto/aes.py',
    'src/trezor/crypto/base58.py',
    'src/trezor/crypto/curve.py',
    'src/trezor/crypto/der.py',
    'src/trezor/crypto/hashlib.py',
    'src/trezor/crypto/hmac.py',
    'src/trezor/crypto/rlp.py',
    'src/trezor/log.py',
    'src/trezor/loop.py',
    'src/trezor/main.py',
    'src/trezor/messages/Address.py',
    'src/trezor/messages/ApplySettings.py',
    'src/trezor/messages/ButtonAck.py',
    'src/trezor/messages/ButtonRequest.py',
    'src/trezor/messages/ButtonRequestType.py',
    'src/trezor/messages/Cancel.py',
    'src/trezor/messages/ChangePin.py',
    'src/trezor/messages/CipherKeyValue.py',
    'src/trezor/messages/CipheredKeyValue.py',
    'src/trezor/messages/ClearSession.py',
    'src/trezor/messages/CoinType.py',
    'src/trezor/messages/DebugLinkDecision.py',
    'src/trezor/messages/DebugLinkFlashErase.py',
    'src/trezor/messages/DebugLinkGetState.py',
    'src/trezor/messages/DebugLinkLog.py',
    'src/trezor/messages/DebugLinkMemory.py',
    'src/trezor/messages/DebugLinkMemoryRead.py',
    'src/trezor/messages/DebugLinkMemoryWrite.py',
    'src/trezor/messages/DebugLinkState.py',
    'src/trezor/messages/DebugLinkStop.py',
    'src/trezor/messages/DecryptMessage.py',
    'src/trezor/messages/DecryptedMessage.py',
    'src/trezor/messages/ECDHSessionKey.py',
    'src/trezor/messages/EncryptMessage.py',
    'src/trezor/messages/EncryptedMessage.py',
    'src/trezor/messages/Entropy.py',
    'src/trezor/messages/EntropyAck.py',
    'src/trezor/messages/EntropyRequest.py',
    'src/trezor/messages/EstimateTxSize.py',
    'src/trezor/messages/EthereumAddress.py',
    'src/trezor/messages/EthereumGetAddress.py',
    'src/trezor/messages/EthereumSignTx.py',
    'src/trezor/messages/EthereumTxAck.py',
    'src/trezor/messages/EthereumTxRequest.py',
    'src/trezor/messages/Failure.py',
    'src/trezor/messages/FailureType.py',
    'src/trezor/messages/Features.py',
    'src/trezor/messages/FirmwareErase.py',
    'src/trezor/messages/FirmwareRequest.py',
    'src/trezor/messages/FirmwareUpload.py',
    'src/trezor/messages/GetAddress.py',
    'src/trezor/messages/GetECDHSessionKey.py',
    'src/trezor/messages/GetEntropy.py',
    'src/trezor/messages/GetFeatures.py',
    'src/trezor/messages/GetPublicKey.py',
    'src/trezor/messages/HDNodePathType.py',
    'src/trezor/messages/HDNodeType.py',
    'src/trezor/messages/IdentityType.py',
    'src/trezor/messages/Initialize.py',
    'src/trezor/messages/InputScriptType.py',
    'src/trezor/messages/LoadDevice.py',
    'src/trezor/messages/MessageSignature.py',
    'src/trezor/messages/MessageType.py',
    'src/trezor/messages/MultisigRedeemScriptType.py',
    'src/trezor/messages/OutputScriptType.py',
    'src/trezor/messages/PassphraseAck.py',
    'src/trezor/messages/PassphraseRequest.py',
    'src/trezor/messages/PinMatrixAck.py',
    'src/trezor/messages/PinMatrixRequest.py',
    'src/trezor/messages/PinMatrixRequestType.py',
    'src/trezor/messages/Ping.py',
    'src/trezor/messages/PublicKey.py',
    'src/trezor/messages/RecoveryDevice.py',
    'src/trezor/messages/RecoveryDeviceType.py',
    'src/trezor/messages/RequestType.py',
    'src/trezor/messages/ResetDevice.py',
    'src/trezor/messages/SetU2FCounter.py',
    'src/trezor/messages/SignIdentity.py',
    'src/trezor/messages/SignMessage.py',
    'src/trezor/messages/SignTx.py',
    'src/trezor/messages/SignedIdentity.py',
    'src/trezor/messages/SimpleSignTx.py',
    'src/trezor/messages/Storage.py',
    'src/trezor/messages/Success.py',
    'src/trezor/messages/TransactionType.py',
    'src/trezor/messages/TxAck.py',
    'src/trezor/messages/TxInputType.py',
    'src/trezor/messages/TxOutputBinType.py',
    'src/trezor/messages/TxOutputType.py',
    'src/trezor/messages/TxRequest.py',
    'src/trezor/messages/TxRequestDetailsType.py',
    'src/trezor/messages/TxRequestSerializedType.py',
    'src/trezor/messages/TxSize.py',
    'src/trezor/messages/VerifyMessage.py',
    'src/trezor/messages/WipeDevice.py',
    'src/trezor/messages/WordAck.py',
    'src/trezor/messages/WordRequest.py',
    'src/trezor/messages/WordRequestType.py',
    'src/trezor/messages/__init__.py',
    'src/trezor/messages/wire_types.py',
    'src/trezor/msg.py',
    'src/trezor/res/__init__.py',
    'src/trezor/res/resources.py',
    'src/trezor/ui/__init__.py',
    'src/trezor/ui/button.py',
    'src/trezor/ui/confirm.py',
    'src/trezor/ui/container.py',
    'src/trezor/ui/keyboard.py',
    'src/trezor/ui/loader.py',
    'src/trezor/ui/pin.py',
    'src/trezor/ui/qr.py',
    'src/trezor/ui/scroll.py',
    'src/trezor/ui/swipe.py',
    'src/trezor/ui/text.py',
    'src/trezor/utils.py',
    'src/trezor/wire/__init__.py',
    'src/trezor/wire/codec_v1.py',
    'src/trezor/wire/codec_v2.py',
    'src/trezor/workflow.py',
]

env = Environment(
    SED='sed',
    AS='arm-none-eabi-as',
    AR='arm-none-eabi-ar',
    CC='arm-none-eabi-gcc',
    LINK='arm-none-eabi-ld',
    SIZE='arm-none-eabi-size',
    STRIP='arm-none-eabi-strip',
    OBJCOPY='arm-none-eabi-objcopy',
    CCFLAGS='-Os '
    '-g3 '
    '-nostdlib '
    '-std=gnu99 -Wall -Werror -Wdouble-promotion -Wpointer-arith '
    '-mthumb -mtune=cortex-m4 -mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard '
    '-fsingle-precision-constant -fdata-sections -ffunction-sections ' +
    CCFLAGS_MOD,
    CCFLAGS_QSTR='-DNO_QSTR -DN_X64 -DN_X86 -DN_THUMB -DN_ARM -DN_XTENSA',
    LINKFLAGS='-nostdlib -T embed/firmware/memory.ld --gc-sections',
    CPPPATH=[
        '.',
        'embed/firmware',
        'embed/trezorhal',
        'embed/trezorhal/hal',
        'embed/extmod/modtrezorui',
        'vendor/micropython',
        'vendor/micropython/stmhal',
        'vendor/micropython/stmhal/cmsis',
        'vendor/micropython/stmhal/hal/f4/inc',
        'vendor/micropython/lib/cmsis/inc',
    ] + CPPPATH_MOD,
    CPPDEFINES=[
        'MICROPY_MODULE_FROZEN_MPY',
        ('MICROPY_QSTR_EXTRA_POOL', 'mp_qstr_frozen_const_pool'),
        ('STM32_HAL_H', '"<stm32f4xx_hal.h>"'),
        'STM32F405xx',
        'TREZOR_STM32',
        'MCU_SERIES_F4',
    ] + CPPDEFINES_MOD,
    PYTHON='python',
    PYTHONPATH='vendor/micropython/py',
    MAKEQSTRDEFS='$PYTHON vendor/micropython/py/makeqstrdefs.py',
    MAKEQSTRDATA='$PYTHON vendor/micropython/py/makeqstrdata.py',
    MAKEVERSIONHDR='$PYTHON vendor/micropython/py/makeversionhdr.py',
    MPY_CROSS='vendor/micropython/mpy-cross/mpy-cross',
    MPY_TOOL='$PYTHON vendor/micropython/tools/mpy-tool.py',
    MAKE_FROZEN='$PYTHON vendor/micropython/tools/make-frozen.py')

env.Tool('micropython')

#
# Micropython version
#

hdr_version = env.Command(
    target='genhdr/mpversion.h',
    source='',
    action='$MAKEVERSIONHDR $TARGET', )

#
# Qstrings
#

qstr_micropython = 'vendor/micropython/py/qstrdefs.h'

qstr_collected = env.CollectQstr(
    target='genhdr/qstrdefs.collected.h',
    source=SOURCE_QSTR)

qstr_preprocessed = env.PreprocessQstr(
    target='genhdr/qstrdefs.preprocessed.h',
    source=[qstr_micropython, qstr_collected])

qstr_generated = env.GenerateQstrDefs(
    target='genhdr/qstrdefs.generated.h',
    source=qstr_preprocessed)

env.Ignore(qstr_collected, qstr_generated)

#
# Frozen modules
#

source_mpy = env.FrozenModule(source=SOURCE_PY)

source_mpyc = env.FrozenCFile(
    target='frozen_mpy.c',
    source=source_mpy,
    qstr_header=qstr_preprocessed)

env.Depends(source_mpyc, qstr_generated)

#
# Program objects
#

obj_firmware = []
obj_firmware += env.Object(source=SOURCE_MOD)
obj_firmware += env.Object(source=SOURCE_FIRMWARE)
obj_firmware += env.Object(source=SOURCE_MICROPYTHON)
obj_firmware += env.Object(source=SOURCE_STMHAL)
obj_firmware += env.Object(source=SOURCE_TREZORHAL)
obj_firmware += env.Object(source=source_mpyc)

env.Depends(obj_firmware, qstr_generated)

env.Command(
    target='firmware.elf',
    source=obj_firmware,
    action=
    '$LINK -o $TARGET $LINKFLAGS $SOURCES `$CC $CFLAGS $CCFLAGS $_CCCOMCOM -print-libgcc-file-name`',
)

env.Command(
    target='firmware.bin',
    source='firmware.elf',
    action='$OBJCOPY -O binary -j .header -j .flash -j .data $SOURCE $TARGET',
)
