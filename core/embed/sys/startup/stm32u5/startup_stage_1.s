  .syntax unified

  .text

  .global reset_handler
  .type reset_handler, STT_FUNC
reset_handler:
  // set the stack protection
  ldr r0, =_stack_section_start
  add r0, r0, #128       // safety margin for the exception frame
  msr MSPLIM, r0

  // setup environment for subsequent stage of code
  ldr r2, =0             // r2 - the word-sized value to be written
  ldr r0, =_startup_clear_ram_0_start
  ldr r1, =_startup_clear_ram_0_end
  bl memset_reg
  ldr r0, =_startup_clear_ram_1_start
  ldr r1, =_startup_clear_ram_1_end
  bl memset_reg
  ldr r0, =_startup_clear_ram_2_start
  ldr r1, =_startup_clear_ram_2_end
  bl memset_reg

  // copy data in from flash
  ldr r0, =_data_section_start     // dst addr
  ldr r1, =_data_section_loadaddr  // src addr
  ldr r2, =_data_section_end       // size in bytes
  sub r2, r2, r0
  bl memcpy

  // copy confidential data in from flash
  ldr r0, =_confidential_section_start // dst addr
  ldr r1, =_confidential_section_loadaddr      // src addr
  ldr r2, =_confidential_section_end   // size in bytes
  sub r2, r2, r0
  bl memcpy

  // setup the stack protector (see build script "-fstack-protector-all") with an unpredictable value
  bl rng_get
  ldr r1, = __stack_chk_guard
  str r0, [r1]

  // copy & clear g_boot_command
  ldr r0, =g_boot_command
  ldr r1, [r0]
  ldr r0, =g_boot_command_saved
  str r1, [r0]
  ldr r0, =g_boot_command
  mov r1, #0
  str r1, [r0]

  // re-enable exceptions
  // according to "ARM Cortex-M Programming Guide to Memory Barrier Instructions" Application Note 321, section 4.7:
  // "If it is not necessary to ensure that a pended interrupt is recognized immediately before
  // subsequent operations, it is not necessary to insert a memory barrier instruction."
  cpsie f

  // enter the application code
  bl main

  b system_exit

  .end
