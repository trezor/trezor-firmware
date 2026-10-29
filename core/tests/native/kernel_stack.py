#!/usr/bin/env python3
"""Static worst-case stack depth of a linked Thumb-2 kernel or secmon ELF.

A function's frame is its largest running SP decrement in instruction order
(push, stmdb, vpush, sub sp). Calls are `bl`/`blx <symbol>`; a branch into
another function is a tail call, which runs after the frame is released.
Indirect calls are listed, not followed, except the known function-pointer
targets in INDIRECT. Noreturn fatal paths end on a fresh stack and are cut.

This is an upper bound for the paths it sees, not a hardware high-water mark:
interrupts, exception stacking and unresolved indirect calls come on top.

    kernel_stack.py kernel.elf --vault
    kernel_stack.py secmon.elf storage_unlock__verified
"""

import argparse
import re
import subprocess
from functools import lru_cache

FUNC = re.compile(r"^[0-9a-f]+ <([^>]+)>:$")
INSN = re.compile(r"^\s*[0-9a-f]+:\s+(\S+)\s*(.*)$")
TARGET = re.compile(r"<([^>+]+)(\+0x[0-9a-f]+)?>")
FATAL = re.compile(
    r"^(__stack_chk_fail|__handle_fault|__fatal_error|__assert_func|"
    r"error_shutdown.*|system_exit.*|systask_exit.*|systask_kill|"
    r"reboot.*|halt_device.*|secure_shutdown|show_.*_error.*)$"
)
CONDITIONAL_B = {
    "b",
    "bcc",
    "bcs",
    "beq",
    "bne",
    "bgt",
    "blt",
    "bge",
    "ble",
    "bhi",
    "bls",
    "bmi",
    "bpl",
}
INDIRECT = {
    "secp256k1_ecdsa_sign_inner": ["secp256k1_nonce_function_rfc6979"],
    "secp256k1_schnorrsig_sign_internal": ["nonce_function_bip340"],
    "mnemonic_to_seed": ["ui_progress"],
}

# Frames from the SVC exception into the vault operations.
SVC_CHAIN = ["SVC_Handler", "svc_handler", "syscall_handler"]
CALL_CHAIN = [
    "vault_call__verified",
    "vault_dispatch",
    "vault_dispatch_inner",
    "vault_execute",
]
# The message entry accepts only VAULT_ED_SIGN.
MESSAGE_CHAIN = [
    "vault_call_message__verified",
    "vault_snapshot_large",
    "vault_dispatch_message",
    "vault_dispatch_inner",
    "vault_execute",
]
ED25519_SIGN = ["ed25519_sign", "ed25519_sign_keccak"]


def reglist_size(ops):
    m = re.search(r"\{([^}]*)\}", ops)
    size = 0
    for part in m.group(1).split(",") if m else []:
        part = part.strip()
        if "-" in part:
            first, last = part.split("-")
            size += int(last[1:]) - int(first[1:]) + 1
        elif part:
            size += 1
    return size


def immediate(ops):
    m = re.search(r"#(-?\d+|0x[0-9a-f]+)", ops)
    return int(m.group(1), 0) if m else 0


def vector_size(ops):
    return reglist_size(ops) * (8 if ops.split("{")[1].lstrip().startswith("d") else 4)


class Program:
    def __init__(self, elf, objdump):
        text = subprocess.check_output(
            [objdump, "-d", "--no-show-raw-insn", elf], text=True
        )
        funcs, current = {}, None
        for line in text.splitlines():
            m = FUNC.match(line)
            if m:
                current = funcs.setdefault(m.group(1), [])
                continue
            m = INSN.match(line)
            if m and current is not None:
                current.append((m.group(1).split(".")[0], m.group(2)))
        self.frame, self.calls, self.tails, self.indirect = {}, {}, {}, {}
        for name, insns in funcs.items():
            self._analyse(name, insns, funcs)
        for name, targets in INDIRECT.items():
            if name in self.calls:
                self.calls[name] |= {t for t in targets if t in self.calls}
                self.indirect[name] = 0

    def _analyse(self, name, insns, funcs):
        depth = peak = indirect = 0
        calls, tails = set(), set()
        for op, ops in insns:
            if op == "push" or (op == "stmdb" and ops.startswith("sp!")):
                depth += 4 * reglist_size(ops)
            elif op == "vpush":
                depth += vector_size(ops)
            elif op == "pop" or (op == "ldmia" and ops.startswith("sp!")):
                depth = max(0, depth - 4 * reglist_size(ops))
            elif op == "vpop":
                depth = max(0, depth - vector_size(ops))
            elif op in ("sub", "subw") and re.match(r"sp,\s*(sp,\s*)?#", ops):
                depth += immediate(ops)
            elif op in ("add", "addw") and re.match(r"sp,\s*(sp,\s*)?#", ops):
                depth = max(0, depth - immediate(ops))
            peak = max(peak, depth)
            target = TARGET.search(ops)
            if op in ("bl", "blx") and target and not ops.startswith("r"):
                calls.add(target.group(1))
            elif op == "blx" or (op == "bx" and not ops.startswith("lr")):
                indirect += 1
            elif (
                op in CONDITIONAL_B
                and target
                and not target.group(2)
                and target.group(1) != name
                and target.group(1) in funcs
            ):
                tails.add(target.group(1))
        self.frame[name], self.calls[name] = peak, calls
        self.tails[name], self.indirect[name] = tails, indirect

    def worst(self, entry):
        """Return (bytes, path) of the deepest call chain from entry."""
        on_path = set()

        @lru_cache(maxsize=None)
        def depth(fn):
            if fn not in self.frame or FATAL.match(fn) or fn in on_path:
                return 0, ()
            on_path.add(fn)
            own = self.frame[fn]
            best, path = own, (f"{fn} {own}",)
            for callee in self.calls[fn]:
                d, p = depth(callee)
                if own + d > best:
                    best, path = own + d, (f"{fn} {own}",) + p
            for callee in self.tails[fn]:
                d, p = depth(callee)
                if d > best:
                    best, path = d, (f"{fn} {own} (tail)",) + p
            on_path.discard(fn)
            return best, path

        return depth(entry)

    def chain(self, names):
        return sum(self.frame.get(name, 0) for name in names)

    def unresolved(self, entry):
        seen, todo = set(), [entry]
        while todo:
            fn = todo.pop()
            if fn in seen or fn not in self.calls or FATAL.match(fn):
                continue
            seen.add(fn)
            todo += list(self.calls[fn]) + list(self.tails[fn])
        return sorted(fn for fn in seen if self.indirect[fn])


def vault_report(program):
    deepest, path = program.worst("SVC_Handler")
    print(f"deepest syscall (path-insensitive): {deepest} B")
    print("  " + " -> ".join(path))
    if "vault_execute" not in program.frame:
        if "vault_call__verified" in program.frame:
            op = program.chain(SVC_CHAIN) + program.worst("vault_call__verified")[0]
            print(f"vault byte op: {op} B")
    else:
        ops = program.calls["vault_execute"] | program.tails["vault_execute"]
        op_depth, op_name = max((program.worst(op)[0], op) for op in ops)
        print(
            f"vault op: {program.chain(SVC_CHAIN + CALL_CHAIN) + op_depth} B"
            f" (deepest: {op_name})"
        )
        if "vault_snapshot_large" in program.frame:
            sign = max(program.worst(fn)[0] for fn in ED25519_SIGN)
            print(
                f"vault Ed25519 message: "
                f"{program.chain(SVC_CHAIN + MESSAGE_CHAIN) + sign} B"
            )
    if "storage_unlock__verified" in program.frame:
        unlock = program.chain(SVC_CHAIN) + program.worst("storage_unlock__verified")[0]
        print(f"storage unlock: {unlock} B")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf")
    parser.add_argument("entries", nargs="*", help="functions to report")
    parser.add_argument(
        "--vault",
        action="store_true",
        help="report the vault and storage syscall paths",
    )
    parser.add_argument("--objdump", default="arm-none-eabi-objdump")
    args = parser.parse_args()
    program = Program(args.elf, args.objdump)
    if args.vault:
        vault_report(program)
    for entry in args.entries:
        if entry not in program.frame:
            print(f"{entry}: absent")
            continue
        total, path = program.worst(entry)
        print(f"{entry}: {total} B")
        print("  " + " -> ".join(path))
        unresolved = program.unresolved(entry)
        if unresolved:
            print("  indirect calls not followed in: " + ", ".join(unresolved))


if __name__ == "__main__":
    main()
