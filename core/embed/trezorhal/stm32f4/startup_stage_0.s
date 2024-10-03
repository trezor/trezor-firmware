  .syntax unified

  .text

  .global reset_handler
  .type reset_handler, STT_FUNC
reset_handler:
  bl SystemInit

  // read the first rng data and save it
  ldr r0, =0            // r0 - previous value
  ldr r1, =0            // r1 - whether to compare the previous value
  bl rng_read

  // read the next rng data and make sure it is different than previous
  // r0 - value returned from previous call
  ldr r1, =1            // r1 - whether to compare the previous value
  bl rng_read
  mov r4, r0            // save TRNG output in r4

  // wipe memory to remove any possible vestiges of sensitive data
  // use unpredictable value as a defense against side-channels
  mov r2, r4            // r2 - the word-sized value to be written
  ldr r0, =_startup_clear_ram_0_start
  ldr r1, =_startup_clear_ram_0_end
  bl memset_reg
  ldr r0, =_startup_clear_ram_1_start
  ldr r1, =_startup_clear_ram_1_end
  bl memset_reg

  // setup environment for subsequent stage of code
  ldr r2, =0             // r2 - the word-sized value to be written
  ldr r0, =_startup_clear_ram_0_start
  ldr r1, =_startup_clear_ram_0_end
  bl memset_reg
  ldr r0, =_startup_clear_ram_1_start
  ldr r1, =_startup_clear_ram_1_end
  bl memset_reg

  // copy data in from flash
  ldr r0, =data_vma     // dst addr
  ldr r1, =data_lma     // src addr
  ldr r2, =data_size    // size in bytes
  bl memcpy

  // setup the stack protector (see build script "-fstack-protector-all")
  // with an unpredictable value
  bl rng_get
  ldr r1, = __stack_chk_guard
  str r0, [r1]

  // Clear the USB FIFO memory to prevent data leakage of sensitive information.
  // This peripheral memory is not cleared by a device reset.
  bl clear_otg_hs_memory

  // enter the application code
  bl main

  b shutdown_privileged

  .end
