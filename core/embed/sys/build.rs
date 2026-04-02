use xbuild::{Result, build_mods};

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

        if cfg!(feature = "lockable_bootloader") {
            lib.add_define("LOCKABLE_BOOTLOADER", None);
        }

        build_mods!(lib;
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
            stack,
            startup,
            task,
            time,
            trustzone if cfg!(feature = "trustzone"),
        );

        Ok(())
    })
}
