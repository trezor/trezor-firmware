  .syntax unified

  .text

  .global reset_handler
  .type reset_handler, STT_FUNC
reset_handler:
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

  ldr r0, =sram6_start   // r0 - point to beginning of SRAM
  ldr r1, =sram6_end     // r1 - point to byte after the end of SRAM
  bl memset_reg

  ldr r0, =sram3_start   // r0 - point to beginning of SRAM
  ldr r1, =__fb_start    // r1 - point to beginning of framebuffer
  bl memset_reg

  ldr r0, =__fb_end      // r0 - point to end of framebuffer
  ldr r1, =sram5_end     // r1 - point to byte after the end of SRAM
  bl memset_reg

  // copy data in from flash
  ldr r0, =data_vma     // dst addr
  ldr r1, =data_lma     // src addr
  ldr r2, =data_size    // size in bytes
  bl memcpy

  // copy sensitive data in from flash
  ldr r0, =sensitive_vma     // dst addr
  ldr r1, =sensitive_lma     // src addr
  ldr r2, =sensitive_size    // size in bytes
  bl memcpy

  // setup the stack protector (see build script "-fstack-protector-all") with an unpredictable value
  bl rng_get
  ldr r1, = __stack_chk_guard
  str r0, [r1]

  //
  ldr r0, =g_boot_flag
  ldr r1, [r0]
  ldr r0, =g_boot_command
  str r1, [r0]
  ldr r0, =g_boot_flag
  mov r1, #0
  str r1, [r0]

  // re-enable exceptions
  // according to "ARM Cortex-M Programming Guide to Memory Barrier Instructions" Application Note 321, section 4.7:
  // "If it is not necessary to ensure that a pended interrupt is recognized immediately before
  // subsequent operations, it is not necessary to insert a memory barrier instruction."
  cpsie f

  // enter the application code
  bl main

  b shutdown_privileged

  .bss

  .global g_boot_command
g_boot_command:
  .word  0

  .end
