fn main() {
    let mut lib = cbuild::CLibrary::new();

    lib.use_lib("io");

    lib.add_source("main.c");

    lib.add_sources(&[
        "../../sys/syscall/stm32/syscall_context.c",
        "../../sys/syscall/stm32/syscall_dispatch.c",
        "../../sys/syscall/stm32/syscall_ipc.c",
        "../../sys/syscall/stm32/syscall_probe.c",
        "../../sys/syscall/stm32/syscall_verifiers.c",
    ]);

    lib.build();

    cbuild::emit_linker_args("kernel");
}
