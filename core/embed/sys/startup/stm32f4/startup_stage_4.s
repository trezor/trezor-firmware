  .syntax unified

  .text

  .global reset_handler
  .type reset_handler, STT_FUNC
reset_handler:

  push {r0, r1}

  // setup the stack protector with provided random value
  ldr r0, = __stack_chk_guard
  str r2, [r0]

  ldr r0, =_bss_section_start
  ldr r1, =0
  ldr r2, =_bss_section_end
  sub r2, r2, r0
  bl memset

  // copy data in from flash
  ldr r0, =_data_section_start     // dst addr
  ldr r1, =_data_section_loadaddr  // src addr
  ldr r2, =_data_section_end       
  sub r2, r2, r0                   // size in bytes
  bl memcpy

  pop {r0, r1}

  // enter the application code
  // returns exit code in r0
  bl main

  // terminate the application
  // pass exit code in r0
  b system_exit

  .end
