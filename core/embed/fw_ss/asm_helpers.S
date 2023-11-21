  .syntax unified

  .text

  .global jump_unsecure

.set SCB_VTOR_NS, 0xE002ED08

jump_unsecure:

    ldr r1, =SCB_VTOR_NS
    str r0, [r1]

    ldr r1, [r0, #0]
    msr MSP_NS, r1

    ldr r1, [r0, #4]
    movs r0, #1
    bics r1, r0 // bit0 == 0 => transition to Non-secure

    bxns r1

