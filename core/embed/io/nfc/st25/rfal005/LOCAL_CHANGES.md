
RFAL middleware was imported into trezor-firmware to support a low level NFC operations of st25r3916b and ST25R210(ST25R500) from
https://www.st.com/en/embedded-software/stsw-st25rfal005.html (version 4.2.0)

# RFAL update 15-Jul-2026:
RFAL middleware updated to version 4.2.0 from  https://www.st.com/en/embedded-software/stsw-st25rfal005.html

# RFAL update 3-Nov-2025:
RFAL middleware updated to version 4.0.2 from  https://www.st.com/en/embedded-software/stsw-st25rfal002.html 

# Local changes

1. rfalIsoDepInfo structure defined in include/rfal_isoDep.h and rfalNfcDepInfo include/rfal_nfcDep.h contains variable DSI which colide with the DSI macro in
STM32 HAL drivers. To resolve this,  variale in RFAL library was refactored to DSI_ID.