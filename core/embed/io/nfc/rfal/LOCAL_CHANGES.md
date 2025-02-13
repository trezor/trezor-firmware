
RFAL middleware was imported into trezor-firmware to support a low level NFC operations of st25r3916b from
https://www.st.com/en/embedded-software/stsw-st25rfal002.html (version 3.0.1)

# Local changes

1. rfalIsoDepInfo structure defined in include/rfal_isoDep.h and rfalNfcDepInfo include/rfal_nfcDep.h contains variable DSI which colide with the DSI macro in
STM32 HAL drivers. To resolve this,  variale in RFAL library was refactored to DSI_ID.