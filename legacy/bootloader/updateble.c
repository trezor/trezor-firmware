//----------------------------------------------------------------------
//      FTSAFE INC COS Kernel : (FIDO)
//----------------------------------------------------------------------
//      File: Update.C
//----------------------------------------------------------------------
//      Update History: (mm/dd/yyyy)
//      06/06/2016 - V1.00 - IQ :  First official release
//----------------------------------------------------------------------
//      Description:
//
//      Use SWD update BLE
//----------------------------------------------------------------------
#include "updateble.h"
#include "layout.h"
#include "swd.h"

// ucErase:1:erase page ;2:eraseall;0:no erase
unsigned char bUBle_beginUpdateFirmware(void) {
  unsigned char res;

  swd_io_init();
  res = swd_dap_init();  //�����˲���
  if (res != 1) {
    return FALSE;
  }
  g_offset = 0;
  return TRUE;
}

/*****************************************************************************
 function:	bUBLE_UpdateBleFirmware
 input:
                ulBleLen:ble firmware len
                ulbleaddr:ble firmware addr
                ucMode:0 :erase app sector 1:erase entire chip
output:
                none
return:
                TRUE/FALSE
******************************************************************************/
unsigned char bUBLE_UpdateBleFirmware(unsigned int ulBleLen,
                                      unsigned int ulbleaddr,
                                      unsigned char ucMode) {
  unsigned int templen;
  unsigned char res;

  templen = ulBleLen;
  // erase
  res = bUBle_beginUpdateFirmware();
  if (res == FALSE) {
    return FALSE;
  }
  // program
  while (templen >= g_page_size) {
    vHAL_Read(ulbleaddr + g_offset, flashram, (unsigned short)g_page_size);
    layoutProgress("INSTALLING BLE firmware...", 1000 * g_offset / ulBleLen);
    res = swd_download(flashram, g_page_size, ucMode);
    if (res != 1) {
      return FALSE;
    }
    g_offset += g_page_size;
    templen -= g_page_size;
  }
  if (templen) {
    memset(flashram, 0, g_page_size);
    vHAL_Read(ulbleaddr + g_offset, flashram, (unsigned short)templen);
    res = swd_download(flashram, g_page_size, ucMode);
    if (res != 1) {
      return FALSE;
    }
    g_offset += templen;
    templen = 0;
  }
  // verify
  layoutProgress("Checking BLE firmware...", 1000);
  res = swd_check_code(ulbleaddr, g_offset, ucMode);
  if (res != 1) {
    return FALSE;
  }
  return TRUE;
}
