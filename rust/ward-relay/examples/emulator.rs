//! Drive a codec-v1 emulator through wardd:
//!
//! ```text
//! cargo run --features codec --example emulator -- sync|flush|status \
//!     [--wardd ws://127.0.0.1:21329] [--token-file ~/.trezor-ward/token] \
//!     [--emulator 127.0.0.1:21324] [--batch N] [--rejoin] [--passphrase P]
//! ```
//!
//! Confirm on the emulator when it asks (or run it with DebugLink auto-confirm).

use std::{env, fs, path::PathBuf};

use ward_relay::{
    codec::{CodecPipe, UdpEmulator},
    WarddClient, WARDD_DEFAULT_URL,
};

fn arg(args: &[String], flag: &str) -> Option<String> {
    args.iter().position(|a| a == flag).and_then(|i| args.get(i + 1).cloned())
}

#[tokio::main(flavor = "current_thread")]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().skip(1).collect();
    let op = args.first().cloned().unwrap_or_else(|| "status".into());
    let url = arg(&args, "--wardd").unwrap_or_else(|| WARDD_DEFAULT_URL.into());
    let token_file = arg(&args, "--token-file").map(PathBuf::from).unwrap_or_else(|| {
        PathBuf::from(env::var("HOME").unwrap_or_default()).join(".trezor-ward/token")
    });
    let token = fs::read_to_string(&token_file)?.trim().to_owned();

    let mut pipe = CodecPipe::new(UdpEmulator::connect(
        &arg(&args, "--emulator").unwrap_or_else(|| "127.0.0.1:21324".into()),
    )?);
    pipe.passphrase = arg(&args, "--passphrase");
    pipe.initialize().map_err(|e| format!("Initialize: {e:?}"))?;

    let mut wardd = WarddClient::connect(&url, &token).await?;
    wardd.open_store(&mut pipe, None, None).await?;
    let result = match op.as_str() {
        "sync" => wardd.sync(&mut pipe, args.iter().any(|a| a == "--rejoin")).await?,
        "flush" => {
            let batch = arg(&args, "--batch").map(|b| b.parse()).transpose()?.unwrap_or(1);
            wardd.flush(&mut pipe, batch).await?
        }
        _ => wardd.status().await?,
    };
    println!("{result}");
    wardd.close().await;
    Ok(())
}
