#ifndef _ILI9341_SPI_H
#define _ILI9341_SPI_H

#define ILI9341_HSYNC ((uint32_t)9) /* Horizontal synchronization */
#define ILI9341_HBP ((uint32_t)29)  /* Horizontal back porch      */
#define ILI9341_HFP ((uint32_t)2)   /* Horizontal front porch     */
#define ILI9341_VSYNC ((uint32_t)1) /* Vertical synchronization   */
#define ILI9341_VBP ((uint32_t)3)   /* Vertical back porch        */
#define ILI9341_VFP ((uint32_t)2)   /* Vertical front porch       */

void ili9341_init(void);

#endif  //_ILI9341_SPI_H
