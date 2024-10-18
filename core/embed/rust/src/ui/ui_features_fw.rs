use crate::{error::Error, micropython::gc::Gc, strutil::TString};

use super::layout::obj::{LayoutMaybeTrace, LayoutObj};

pub trait UIFeaturesFirmware {
    fn show_info(
        title: TString<'static>,
        description: TString<'static>,
        button: TString<'static>,
        time_ms: u32,
    ) -> Result<Gc<LayoutObj>, Error>;
}
