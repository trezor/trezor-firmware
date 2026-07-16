use xbuild::{Result, build_mods};

#[path = "bsp/build.rs"]
mod bsp;
#[path = "cpuid/build.rs"]
mod cpuid;
#[path = "dbg/build.rs"]
mod dbg;
#[path = "flash/build.rs"]
mod flash;
#[path = "i2c_bus/build.rs"]
mod i2c_bus;
#[path = "ipc/build.rs"]
mod ipc;
#[path = "irq/build.rs"]
mod irq;
#[path = "linker/build.rs"]
mod linker;
#[path = "mpu/build.rs"]
mod mpu;
#[path = "pvd/build.rs"]
mod pvd;
#[path = "rng/build.rs"]
mod rng;
#[path = "sdram/build.rs"]
mod sdram;
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
        lib.import_lib("crypto")?;

        lib.add_includes([
            "syscall/inc", // temporary hack
            "inc",
            "../../vendor",
        ]);

        if cfg!(feature = "boot_ucb") {
            lib.add_define("USE_BOOT_UCB", Some("1"));
        }

        // Hardware-derived storage key (BHK) is an stm32u5 feature only,
        // and the emulator has no BHK regardless of which MCU it emulates.
        if cfg!(feature = "mcu_stm32u5") && cfg!(not(feature = "emulator")) {
            lib.add_define("USE_STORAGE_HWKEY", Some("1"));
        }

        if cfg!(feature = "lockable_bootloader") {
            lib.add_define("LOCKABLE_BOOTLOADER", None);
        }

        build_mods!(
            lib,
            [
                bsp,
                cpuid,
                dbg if cfg!(feature = "dbg_console"),
                i2c_bus if cfg!(feature = "i2c_bus"),
                ipc if cfg!(feature = "ipc"),
                irq,
                flash,
                linker if cfg!(not(feature = "emulator")),
                mpu,
                pvd if cfg!(feature = "pvd"),
                rng,
                sdram if cfg!(feature = "sdram"),
                stack,
                startup,
                task,
                time,
                trustzone if cfg!(feature = "trustzone"),
            ]
        );

        Ok(())
    })
}
