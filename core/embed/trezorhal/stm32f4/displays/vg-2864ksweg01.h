#ifndef _VG_2864KSWEG01_H
#define _VG_2864KSWEG01_H

#define MAX_DISPLAY_RESX 128
#define MAX_DISPLAY_RESY 64
#define DISPLAY_RESX 128
#define DISPLAY_RESY 64
#define TREZOR_FONT_BPP 1

void pixeldata_dirty(void);
#define PIXELDATA_DIRTY() pixeldata_dirty();

#endif  //_VG_2864KSWEG01_H
