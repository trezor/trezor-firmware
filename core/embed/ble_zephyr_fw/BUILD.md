## Build in the directory above `testapp3`

Move or symlink into `ncs` root dir the app:

In the shell in `/path/to/ncs` where this is named `testapp3`:

        west -v build -b t3w1_nrf52833 testapp3 -- -Dmcuboot_OVERLAY_CONFIG=/home/ondro/work/satoshilabs/repos/ncs/testapp3/mcuboot.conf

!!! The previous build will get stuck in bootloader serial recovery since not sure which pin triggers it:

        west build -b t3w1_nrf52833 testapp3 -- -Dmcuboot_OVERLAY_CONFIG=/home/ondro/work/satoshilabs/repos/ncs/testapp3/mcuboot.conf.without_serial_recovery

Name of the directory doesn't seem to matter, just replace it then as argument in the build invocations.

## Nobody know WTF this is what it wants
        warning: The choice symbol MCUBOOT_BOOTLOADER_MODE_SINGLE_APP (defined at
        modules/Kconfig.mcuboot:149) was selected (set =y), but no symbol ended up as the choice selection.
        See http://docs.zephyrproject.org/latest/kconfig.html#CONFIG_MCUBOOT_BOOTLOADER_MODE_SINGLE_APP
        and/or look up MCUBOOT_BOOTLOADER_MODE_SINGLE_APP in the menuconfig/guiconfig interface. The

## update via mcumgr boha jeho

List slots:

        /home/ondro/work/satoshilabs/repos/ncs/mcumgr-client/target/debug/mcumgr-client -d /dev/ttyUSB0 -v list

Updated signed app upload - works, needs reset

        /home/ondro/work/satoshilabs/repos/ncs/mcumgr-client/target/debug/mcumgr-client -d /dev/ttyUSB0 -s 0 upload build/zephyr/app_update.bin
        /home/ondro/work/satoshilabs/repos/ncs/mcumgr-client/target/debug/mcumgr-client -d /dev/ttyUSB0 reset

Other baudrate:

        /home/ondro/work/satoshilabs/repos/ncs/mcumgr-client/target/debug/mcumgr-client -d /dev/ttyUSB0 -s 0 -b 460800 upload build/zephyr/app_update.bin
        /home/ondro/work/satoshilabs/repos/ncs/mcumgr-client/target/debug/mcumgr-client -d /dev/ttyUSB0 -b 460800 reset
        /home/ondro/work/satoshilabs/repos/ncs/mcumgr-client/target/debug/mcumgr-client -d /dev/ttyUSB0 -b 460800 -v list

## CLion hack to make resolving symbols work:

- comment out line `CONFIG_BOOTLOADER_MCUBOOT=y` in prj.conf
- comment out whole `settings` partition in pm_static.yml
