use crate::{error::Error, micropython::obj::Obj, strutil::TString};

pub trait UIFeaturesFirmware {
    fn show_info(
        title: TString<'static>,
        button: TString<'static>,
        description: TString<'static>,
        allow_cancel: bool,
        time_ms: u32,
    ) -> Result<Obj, Error>;
}
