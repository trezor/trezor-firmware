/* STM32F205RE - 512K Flash, 128K RAM */
/* program starts at 0x08010000 */
MEMORY
{
	rom (rx) : ORIGIN = 0x08004000, LENGTH = 512K - 16K
	ram (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
}

INCLUDE libopencm3_stm32f2.ld
