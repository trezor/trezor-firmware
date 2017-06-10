/* STM32F205RE - 512K Flash, 128K RAM */
/* program starts at 0x08010000 */
MEMORY
{
	rom (rx)        : ORIGIN = 0x08010000, LENGTH = 512K - 64K
	bootloader (rx) : ORIGIN = 0x20000000, LENGTH = __bootloader_size__
	ram (rwx)       : ORIGIN = ORIGIN(bootloader) + LENGTH(bootloader),
			  LENGTH = 128K - LENGTH(bootloader)
}

INCLUDE libopencm3_stm32f2.ld

SECTIONS
{
	.bootloader : {
		__bootloader_runaddr__ = .;
		KEEP (*(.bootloader*))
	} >bootloader AT >rom

	__bootloader_loadaddr__ = LOADADDR(.bootloader);
}
