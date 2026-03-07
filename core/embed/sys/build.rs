#[path = "bsp/build.rs"]
mod bsp;

#[path = "cpuid/build.rs"]
mod cpuid;

#[path = "i2c_bus/build.rs"]
mod i2c_bus;

#[path = "irq/build.rs"]
mod irq;

#[path = "flash/build.rs"]
mod flash;

#[path = "linker/build.rs"]
mod linker;

#[path = "mpu/build.rs"]
mod mpu;

#[path = "pvd/build.rs"]
mod pvd;

#[path = "rng/build.rs"]
mod rng;

#[path = "stack/build.rs"]
mod stack;

#[path = "startup/build.rs"]
mod startup;

#[path = "task/build.rs"]
mod task;

#[path = "time/build.rs"]
mod time;

#[path = "trustzone/build.rs"]
mod trustzone;

fn main() {
    let mut lib = cbuild::CLibrary::new();

    lib.use_lib("rtl");

    lib.add_public_includes(&[
        "syscall/inc", // temporary hack
        "inc",
        "../../vendor",
    ]);

    if cfg!(feature = "boot_ucb") {
        lib.add_public_define("USE_BOOT_UCB", Some("1"));
    }

    bsp::def_module(&mut lib);

    cpuid::def_module(&mut lib);

    if cfg!(feature = "i2c_bus") {
        i2c_bus::def_module(&mut lib);
    }

    irq::def_module(&mut lib);

    flash::def_module(&mut lib);

    if !cfg!(feature = "mcu_emulator") {
        linker::def_module(&mut lib);
    }

    mpu::def_module(&mut lib);

    if cfg!(feature = "pvd") {
        pvd::def_module(&mut lib);
    }

    rng::def_module(&mut lib);

    stack::def_module(&mut lib);

    startup::def_module(&mut lib);

    task::def_module(&mut lib);

    time::def_module(&mut lib);

    if cfg!(feature = "trustzone") {
        trustzone::def_module(&mut lib);
    }

    lib.build();
}
