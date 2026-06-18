fn do_main() -> Result<(), trezor_client::Error> {
    // init with debugging
    let mut trezor = trezor_client::unique(true)?;
    trezor.init_device(None)?;

    trezor.change_pin(false)?;

    Ok(())
}

fn main() {
    do_main().unwrap()
}
