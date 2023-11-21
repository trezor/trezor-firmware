    .syntax unified

    .text

    .global jump_unprivileged


// jump_unprivileged() can be called only from an exception handler
// (handler mode)

jump_unprivileged:

    ldr r12, [r0, #0]   // stack pointer
    sub r12, r12, #32
    msr PSP, r12

    ldr r1, [r0, #0]
    sub r1, r1, #16384  // stack limit
    msr PSPLIM, r1

    mov r1, #0
    str r1, [r12, #0]    // r0
    str r1, [r12, #4]    // r1
    str r1, [r12, #8]    // r2
    str r1, [r12, #12]   // r3
    str r1, [r12, #16]   // r12
    str r1, [r12, #20]   // lr

    ldr r1, [r0, #4]     // reset vector
    bic r1, r1, #1
    str r1, [r12, #24]   // return address

    ldr r1, = 0x01000000
    str r1, [r12, #28]   // xPSR

    // set thread mode to unprivileged level
    mrs r1, CONTROL
    orr r1, r1, #1
    msr CONTROL, r1

    // return to Non-Secure Thread mode
    // use Non-Secure PSP
    ldr lr, = 0xFFFFFFBC
    bx  lr

    .end

