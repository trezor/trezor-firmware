This PR adds a set of countermeasures against fault injection attacks that become relevant once external (third-party) apps are supported. Production devices will only run apps that are signed and reviewed, but these measures are still useful as defense in depth: they harden the boundary between the kernel and an unprivileged task so that a single glitched instruction is no longer enough to cross it.

- **Illegal SVC numbers terminate the calling task**, and the SVC used for task switching is rejected when invoked from an unprivileged task. Both were harmless before, but they gave an attacker a free and precisely timed trigger of the kernel's context switch path.

- **Terminated tasks are never scheduled again.** Yielding to a killed task is now a fatal error. This guards against logic errors in the kernel as well as against state corrupted by fault injection.

- **Clearing nPRIV during a context switch is hardened.** The privilege level is first lowered unconditionally, then raised only for the kernel task after two independent checks, and finally read back. If an unprivileged task would end up privileged, the kernel shuts down.

- **The MPU mode of an unprivileged task is no longer captured from the live MPU state when the task is switched out.** Instead, the live state is compared against the mode the task is expected to have, and a mismatch is fatal. Previously, a kernel bug (e.g. an IRQ handler that does not call `mpu_restore()`) or a glitch would have become the task's permanent MPU mode.

- **Reading the PC of a crashed task from its stack is hardened.** This value is shown on the RSOD, and a glitched bounds check could previously turn it into a read of an arbitrary memory location, including secrets. In the kernel the read is now done with an unprivileged load (`LDRT`), so the hardware enforces the task's own permissions. In the secmon the read goes through the Non-Secure alias, so secure memory cannot be reached, and the value is accepted only if it looks like a genuine return address.

- **`syscall_handler()` is split into `syscall_handler_default()` and `syscall_handler_limited()`.** Each applet is assigned its handler when it is created, and the limited handler contains only the syscalls available to external apps. This removes the single privilege check that every syscall used to pass through, which was an obvious target for fault injection.


---

This PR hardens the boundary between the kernel and unprivileged tasks in
preparation for external app support. The changes improve robustness against
fault injection and against kernel logic errors, and are intended as defense
in depth.

- Illegal SVC numbers terminate the calling task. The SVC used for task
  switching is accepted only from the kernel task.
- Yielding to a terminated task is a fatal error.
- During a context switch, nPRIV is lowered first, raised only for the kernel-
  task, and the result is verified.
- The MPU mode of an unprivileged task is fixed at task creation and verified
  when the task is switched out.
- The return address of a crashed task is read with the permissions of the
  faulting context (an unprivileged load in the kernel, the Non-Secure alias
  in the secmon) and is validated before it is shown on the RSOD.
- `syscall_handler()` is split into `syscall_handler_default()` and
  `syscall_handler_limited()`. Each applet is assigned its handler when it is
  created.