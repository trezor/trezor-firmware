use std::io;

fn read_pin() -> String {
    println!("Enter PIN");
    let mut pin = String::new();
    if io::stdin().read_line(&mut pin).unwrap() != 5 {
        println!("must enter pin, received: {}", pin);
    }
    // trim newline
    pin[..4].to_owned()
}

fn do_main() -> Result<(), trezor_client::Error> {
    // init with debugging
    let mut trezor = trezor_client::unique(true)?;
    trezor.init_device(None)?;

    let old_pin = trezor.change_pin(false)?.button_request()?.ack()?.pin_matrix_request()?;

    let new_pin1 = old_pin.ack_pin(read_pin())?.pin_matrix_request()?;

    let new_pin2 = new_pin1.ack_pin(read_pin())?.pin_matrix_request()?;

    new_pin2.ack_pin(read_pin())?.ok()?;

    Ok(())
}

fn main() {
    do_main().unwrap()
}
