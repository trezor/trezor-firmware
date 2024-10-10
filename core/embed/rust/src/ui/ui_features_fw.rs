use crate::{error::Error, strutil::TString};

use super::layout::obj::LayoutMaybeTrace;

pub trait UIFeaturesFirmware {
    fn show_info(
        title: TString<'static>,
        button: TString<'static>,
        description: TString<'static>,
    ) -> Result<impl LayoutMaybeTrace, Error>;
}
