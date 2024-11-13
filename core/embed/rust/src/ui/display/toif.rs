use crate::{
    error::{value_error, Error},
    ui::geometry::Offset,
};

const TOIF_HEADER_LENGTH: usize = 12;

#[derive(PartialEq, Debug, Eq, FromPrimitive, Clone, Copy)]
pub enum ToifFormat {
    FullColorBE = 0, // big endian
    GrayScaleOH = 1, // odd hi
    FullColorLE = 2, // little endian
    GrayScaleEH = 3, // even hi
}

/// Holding toif data
/// See https://docs.trezor.io/trezor-firmware/misc/toif.html for data format.
#[derive(PartialEq, Eq, Clone, Copy)]
pub struct Toif<'i> {
    data: &'i [u8],
}

impl<'i> Toif<'i> {
    pub const fn new(data: &'i [u8]) -> Result<Self, Error> {
        if data.len() < TOIF_HEADER_LENGTH || data[0] != b'T' || data[1] != b'O' || data[2] != b'I'
        {
            return Err(value_error!(c"Invalid TOIF header."));
        }
        let zdatalen = u32::from_le_bytes([data[8], data[9], data[10], data[11]]) as usize;
        if zdatalen + TOIF_HEADER_LENGTH != data.len() {
            return Err(value_error!(c"Invalid TOIF length."));
        }
        Ok(Self { data })
    }

    pub const fn format(&self) -> ToifFormat {
        match self.data[3] {
            b'f' => ToifFormat::FullColorBE,
            b'g' => ToifFormat::GrayScaleOH,
            b'F' => ToifFormat::FullColorLE,
            b'G' => ToifFormat::GrayScaleEH,
            _ => panic!(),
        }
    }

    pub const fn is_grayscale(&self) -> bool {
        matches!(
            self.format(),
            ToifFormat::GrayScaleOH | ToifFormat::GrayScaleEH
        )
    }

    pub const fn width(&self) -> i16 {
        u16::from_le_bytes([self.data[4], self.data[5]]) as i16
    }

    pub const fn height(&self) -> i16 {
        u16::from_le_bytes([self.data[6], self.data[7]]) as i16
    }

    pub const fn size(&self) -> Offset {
        Offset::new(self.width(), self.height())
    }

    pub fn zdata(&self) -> &'i [u8] {
        &self.data[TOIF_HEADER_LENGTH..]
    }

    pub fn original_data(&self) -> &'i [u8] {
        self.data
    }
}

#[derive(PartialEq, Eq, Clone, Copy)]
pub struct Icon {
    pub toif: Toif<'static>,
    #[cfg(feature = "ui_debug")]
    pub name: &'static str,
}

impl Icon {
    pub const fn new(data: &'static [u8]) -> Self {
        let toif = match Toif::new(data) {
            Ok(t) => t,
            _ => panic!("Invalid image."),
        };
        assert!(matches!(toif.format(), ToifFormat::GrayScaleEH));
        Self {
            toif,
            #[cfg(feature = "ui_debug")]
            name: "<unnamed>",
        }
    }

    /// Create a named icon.
    /// The name is only stored in debug builds.
    pub const fn debug_named(data: &'static [u8], _name: &'static str) -> Self {
        Self {
            #[cfg(feature = "ui_debug")]
            name: _name,
            ..Self::new(data)
        }
    }
}
