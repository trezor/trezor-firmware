use crate::{args::FmtArgs, helpers};
use anyhow::Result;

mod python;
mod rust;
mod translations;

pub fn format(args: FmtArgs) -> Result<()> {
    let packages = helpers::selected_packages(&args.package)?;

    rust::format(args.check, &packages)?;

    for package in &packages {
        let package_dir = helpers::package_dir(package)?;
        translations::format(package_dir.join("translations"), args.check)?;
        python::format(package_dir.join("tests"), args.check)?;
    }

    Ok(())
}
