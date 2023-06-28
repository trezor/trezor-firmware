  .syntax unified

  .text

  .global reset_handler
  .type reset_handler, STT_FUNC
reset_handler:

// The following loading of VTOR address only works if T1 bootloader was built with PRODUCTION=0
// or the firmware was properly signed. All other variants end up in hard fault due to MPU
// (cf mpu_config_firmware in legacy bootloader)


  // setup environment for subsequent stage of code

  ldr r2, =0             // r2 - the word-sized value to be written

  ldr r0, =sram1_start   // r0 - point to beginning of SRAM
  ldr r1, =sram1_end     // r1 - point to byte after the end of SRAM
  bl memset_reg

  ldr r0, =sram2_start   // r0 - point to beginning of SRAM
  ldr r1, =sram2_end     // r1 - point to byte after the end of SRAM
  bl memset_reg

  ldr r0, =sram4_start   // r0 - point to beginning of SRAM
  ldr r1, =sram4_end     // r1 - point to byte after the end of SRAM
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
  cpsie f

  // enter the application code
  bl main

  b shutdown_privileged

  .global MemManage_Handler
  .type MemManage_Handler, STT_FUNC
MemManage_Handler:
  ldr r2, =_sstack
  mrs r1, msp
  ldr r0, =_estack
  msr msp, r0
  cmp r1, r2
  IT lt
  bllt MemManage_Handler_SO
  bl MemManage_Handler_MM

  .end
