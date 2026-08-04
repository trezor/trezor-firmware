fn main() -> anyhow::Result<()> {
    trezor_app_build::build_protobufs()?;
    trezor_app_build::build_translations()?;
    trezor_app_build::link()?;
    Ok(())
}
