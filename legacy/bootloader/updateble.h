#ifndef _UPDATEBLE_H_
#define _UPDATEBLE_H_

#define ERASE_PAGE 1
#define ERASE_ALL 2

#define FALSE 0
#define TRUE 1

unsigned char bUBLE_UpdateBleFirmware(unsigned int ulBleLen,
                                      unsigned int ulbleaddr,
                                      unsigned char ucMode);

#endif
