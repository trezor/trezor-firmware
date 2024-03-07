use std::str::FromStr;

use bitcoin::bip32::DerivationPath;
use trezor_client::utils::convert_path;

fn do_main() -> Result<(), trezor_client::Error> {
    let mut trezor = trezor_client::unique(false)?;
    trezor.init_device(None)?;
    let path = DerivationPath::from_str("m/44'/501'/0'/0'").expect("Hardended Derivation Path");
    let solana_address = trezor.solana_get_address(convert_path(&path))?;
    println!("solana address: {:?}", solana_address);
    Ok(())
}

fn main() {
    do_main().unwrap()
}
