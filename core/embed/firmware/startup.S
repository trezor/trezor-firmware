  .syntax unified

  .text

  .global reset_handler
  .type reset_handler, STT_FUNC
reset_handler:

// The following loading of VTOR address only works if T1 bootloader was built with MEMORY_PROTECT=0
// or the firmware was properly signed. All other variants end up in hard fault due to MPU
// (cf mpu_config_firmware in legacy bootloader)

#if TREZOR_MODEL == 1
  cpsid if
  ldr r0, =0xE000ED08  // r0 = VTOR address
  ldr r1, =0x08010400  // r1 = FLASH_APP_START
  str r1, [r0]         // assign

  ldr r0, =_estack - 8  // r0 = stack pointer, T1 bootloader had 8 bytes reserved at end
  msr msp, r0           // set stack pointer
  dsb
  isb
#endif

  // setup environment for subsequent stage of code
  ldr r0, =ccmram_start // r0 - point to beginning of CCMRAM
  ldr r1, =ccmram_end   // r1 - point to byte after the end of CCMRAM
  ldr r2, =0            // r2 - the word-sized value to be written
  bl memset_reg

  ldr r0, =sram_start   // r0 - point to beginning of SRAM
  ldr r1, =sram_end     // r1 - point to byte after the end of SRAM
  ldr r2, =0            // r2 - the word-sized value to be written
  bl memset_reg

  // copy data in from flash
  ldr r0, =data_vma     // dst addr
  ldr r1, =data_lma     // src addr
  ldr r2, =data_size    // size in bytes
  bl memcpy

  // setup the stack protector (see build script "-fstack-protector-all") with an unpredictable value
  bl rng_get
  ldr r1, = __stack_chk_guard
  str r0, [r1]

  // re-enable exceptions
  // according to "ARM Cortex-M Programming Guide to Memory Barrier Instructions" Application Note 321, section 4.7:
  // "If it is not necessary to ensure that a pended interrupt is recognized immediately before
  // subsequent operations, it is not necessary to insert a memory barrier instruction."
#if TREZOR_MODEL == T
  cpsie f
#elif TREZOR_MODEL == 1
  cpsie if
#endif

  // enter the application code
  bl main

  b shutdown_privileged

  .end
