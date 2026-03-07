fn main() {
    let mut lib = cbuild::CLibrary::new();

    lib.use_lib("sec");

    lib.add_include(".");

    lib.add_source("main.c");
    lib.add_source("header.S");

    lib.add_sources(&[
        "../../sys/smcall/stm32/smcall_dispatch.c",
        "../../sys/smcall/stm32/smcall_probe.c",
        "../../sys/smcall/stm32/smcall_verifiers.c",
    ]);

    lib.build();

    cbuild::emit_linker_args("secmon");
}
