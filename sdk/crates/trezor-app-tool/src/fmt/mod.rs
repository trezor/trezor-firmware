use crate::{args::FmtArgs, helpers, pygen};
use anyhow::Result;

mod python;
mod rust;
mod translations;

pub fn format(args: FmtArgs) -> Result<()> {
    let packages = helpers::selected_packages(&args.package)?;

    rust::format(args.check, &packages)?;

    // pyright is run from the workspace's `pyrightconfig.json`, which covers
    // the tests of all apps (not just the selected ones), and those import
    // the generated message definitions.
    for package in &helpers::selected_packages(&[])? {
        pygen::generate(helpers::package_dir(package)?)?;
    }

    for package in &packages {
        let package_dir = helpers::package_dir(package)?;
        translations::format(package_dir, args.check)?;
        python::format(package_dir, args.check)?;
    }

    Ok(())
}
