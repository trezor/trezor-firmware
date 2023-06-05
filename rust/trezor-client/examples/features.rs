use std::io;

fn convert_path_from_str(derivation: &str) -> Vec<u32> {
    let derivation = derivation.to_string();
    let elements = derivation.split('/').skip(1).collect::<Vec<_>>();

    let mut path = vec![];
    for derivation_index in elements {
        let hardened = derivation_index.contains('\'');
        let mut index = derivation_index.replace('\'', "").parse::<u32>().unwrap();
        if hardened {
            index |= 0x80000000;
        }
        path.push(index);
    }

    path
}

fn device_selector() -> trezor_client::Trezor {
    let mut devices = trezor_client::find_devices(false);

    if devices.is_empty() {
        panic!("No devices connected");
    } else if devices.len() == 1 {
        devices.remove(0).connect().expect("connection error")
    } else {
        println!("Choose device:");
        for (i, dev) in devices.iter().enumerate() {
            println!("{}: {}", i + 1, dev);
        }
        println!("Enter device number: ");
        let mut inp = String::new();
        io::stdin().read_line(&mut inp).expect("stdin error");
        let idx: usize = inp[..inp.len() - 1].parse().expect("invalid number");
        if idx >= devices.len() {
            panic!("Index out of range");
        }
        devices.remove(idx).connect().unwrap()
    }
}

fn do_main() -> Result<(), trezor_client::Error> {
    // init with debugging
    tracing_subscriber::fmt().with_max_level(tracing::Level::TRACE).init();

    let mut trezor = device_selector();
    trezor.init_device(None)?;
    let f = trezor.features().expect("no features").clone();

    println!("Features:");
    println!("vendor: {}", f.vendor());
    println!("version: {}.{}.{}", f.major_version(), f.minor_version(), f.patch_version());
    println!("device id: {}", f.device_id());
    println!("label: {}", f.label());
    println!("is initialized: {}", f.initialized());
    println!("pin protection: {}", f.pin_protection());
    println!("passphrase protection: {}", f.passphrase_protection());
    println!(
        "{:?}",
        trezor.ethereum_get_address(convert_path_from_str("m/44'/60'/1'/0/0")).unwrap()
    );
    drop(trezor);

    let mut trezor2 = device_selector();

    trezor2.init_device(Some(f.session_id().to_vec()))?;

    println!(
        "{:?}",
        trezor2.ethereum_get_address(convert_path_from_str("m/44'/60'/1'/0/0")).unwrap()
    );
    //optional bool bootloader_mode = 5;          // is device in bootloader mode?
    //optional string language = 9;               // device language
    //optional bytes revision = 13;               // SCM revision of firmware
    //optional bytes bootloader_hash = 14;        // hash of the bootloader
    //optional bool imported = 15;                // was storage imported from an external source?
    //optional bool pin_cached = 16;              // is PIN already cached in session?
    //optional bool passphrase_cached = 17;       // is passphrase already cached in session?
    //optional bool firmware_present = 18;        // is valid firmware loaded?
    //optional bool needs_backup = 19;            // does storage need backup? (equals to
    // Storage.needs_backup) optional uint32 flags = 20;                 // device flags (equals
    // to Storage.flags) optional string model = 21;                 // device hardware model
    //optional uint32 fw_major = 22;              // reported firmware version if in bootloader
    // mode optional uint32 fw_minor = 23;              // reported firmware version if in
    // bootloader mode optional uint32 fw_patch = 24;              // reported firmware version
    // if in bootloader mode optional string fw_vendor = 25;             // reported firmware
    // vendor if in bootloader mode optional bytes fw_vendor_keys = 26;         // reported
    // firmware vendor keys (their hash) optional bool unfinished_backup = 27;       // report
    // unfinished backup (equals to Storage.unfinished_backup) optional bool no_backup = 28;
    // // report no backup (equals to Storage.no_backup)

    Ok(())
}

fn main() {
    do_main().unwrap()
}
