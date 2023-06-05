fn main() {
    let trezors = trezor_client::find_devices(false);
    println!("Found {} devices: ", trezors.len());
    for t in trezors.into_iter() {
        println!("- {}", t);
        {
            let mut client = t.connect().unwrap();
            println!("{:?}", client.initialize(None).unwrap());
        }
    }
}
