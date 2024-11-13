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

/// Holding toif data and allowing it to draw itself.
/// See https://docs.trezor.io/trezor-firmware/misc/toif.html for data format.
#[derive(PartialEq, Eq, Clone, Copy)]
pub struct Toif<'i> {
    data: &'i [u8],
    /// Due to toif limitations, image width must be divisible by 2.
    /// In cases the actual image is odd-width, it will have empty
    /// rightmost column and this flag will make account for it
    /// when determining the width and when drawing it.
    pub empty_right_column: bool,
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
        Ok(Self {
            data,
            empty_right_column: false,
        })
    }

    pub const fn with_empty_right_column(mut self) -> Self {
        self.empty_right_column = true;
        self
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
        let data_width = u16::from_le_bytes([self.data[4], self.data[5]]) as i16;
        if self.empty_right_column {
            data_width - 1
        } else {
            data_width
        }
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

    pub const fn with_empty_right_column(mut self) -> Self {
        self.toif.empty_right_column = true;
        self
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
