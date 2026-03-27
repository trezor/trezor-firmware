use xbuild::Result;

#[path = "bsp/build.rs"]
mod bsp;

#[path = "cpuid/build.rs"]
mod cpuid;

#[path = "dbg/build.rs"]
mod dbg;

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

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("rtl")?;

        lib.add_includes([
            "syscall/inc", // temporary hack
            "inc",
            "../../vendor",
        ]);

        if cfg!(feature = "boot_ucb") {
            lib.add_define("USE_BOOT_UCB", Some("1"));
        }

        if cfg!(feature = "storage_hw_key") {
            lib.add_define("USE_STORAGE_HWKEY", Some("1"));
        }

        bsp::def_module(lib)?;

        cpuid::def_module(lib)?;

        if cfg!(feature = "dbg_console") {
            dbg::def_module(lib)?;
        }

        if cfg!(feature = "i2c_bus") {
            i2c_bus::def_module(lib)?;
        }

        irq::def_module(lib)?;

        flash::def_module(lib)?;

        if cfg!(not(feature = "emulator")) {
            linker::def_module(lib);
        }

        mpu::def_module(lib)?;

        if cfg!(feature = "pvd") {
            pvd::def_module(lib)?;
        }

        rng::def_module(lib)?;

        stack::def_module(lib)?;

        startup::def_module(lib)?;

        task::def_module(lib)?;

        time::def_module(lib)?;

        if cfg!(feature = "trustzone") {
            trustzone::def_module(lib)?;
        }

        Ok(())
    })
}
