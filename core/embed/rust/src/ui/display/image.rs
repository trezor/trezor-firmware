use crate::io::BinaryData;
use crate::ui::geometry::Offset;

impl<'a> BinaryData<'a> {
    fn read_u8(&self, ofs: usize) -> Option<u8> {
        let mut buff: [u8; 1] = [0; 1];
        if self.read(ofs, buff.as_mut()) == buff.len() {
            Some(buff[0])
        } else {
            None
        }
    }

    fn read_u16_le(&self, ofs: usize) -> Option<u16> {
        let mut buff: [u8; 2] = [0; 2];
        if self.read(ofs, buff.as_mut()) == buff.len() {
            Some(u16::from_le_bytes(buff))
        } else {
            None
        }
    }

    fn read_u16_be(&self, ofs: usize) -> Option<u16> {
        let mut buff: [u8; 2] = [0; 2];
        if self.read(ofs, buff.as_mut()) == buff.len() {
            Some(u16::from_be_bytes(buff))
        } else {
            None
        }
    }

    fn read_u32_le(&self, ofs: usize) -> Option<u32> {
        let mut buff: [u8; 4] = [0; 4];
        if self.read(ofs, buff.as_mut()) == buff.len() {
            Some(u32::from_le_bytes(buff))
        } else {
            None
        }
    }
}

#[derive(PartialEq, Debug, Eq, FromPrimitive, Clone, Copy)]
pub enum ToifFormat {
    FullColorBE = 0, // big endian
    GrayScaleOH = 1, // odd hi
    FullColorLE = 2, // little endian
    GrayScaleEH = 3, // even hi
}

pub struct ToifInfo {
    format: ToifFormat,
    size: Offset,
    len: usize,
}

impl ToifInfo {
    pub const HEADER_LENGTH: usize = 12;

    pub fn parse(image: BinaryData) -> Option<Self> {
        let mut prefix = [0u8; 4];
        if image.read(0, prefix.as_mut()) != prefix.len() {
            return None;
        }
        if prefix[..3] != *b"TOI" {
            return None;
        }
        let format = match prefix[3] {
            b'f' => ToifFormat::FullColorBE,
            b'g' => ToifFormat::GrayScaleOH,
            b'F' => ToifFormat::FullColorLE,
            b'G' => ToifFormat::GrayScaleEH,
            _ => return None,
        };

        let width = image.read_u16_le(4)?;
        let height = image.read_u16_le(6)?;
        let len = image.read_u32_le(8)? as usize;

        if width > 1024 || height > 1024 || len > 65536 {
            return None;
        }

        if len + Self::HEADER_LENGTH != image.len() {
            return None;
        }

        Some(Self {
            format,
            size: Offset::new(width as i16, height as i16),
            len,
        })
    }

    pub fn format(&self) -> ToifFormat {
        self.format
    }

    pub fn size(&self) -> Offset {
        self.size
    }

    pub fn width(&self) -> i16 {
        self.size.x
    }

    pub fn height(&self) -> i16 {
        self.size.y
    }

    pub fn is_grayscale(&self) -> bool {
        matches!(
            self.format,
            ToifFormat::GrayScaleOH | ToifFormat::GrayScaleEH
        )
    }

    pub fn stride(&self) -> usize {
        if self.is_grayscale() {
            (self.width() + 1) as usize / 2
        } else {
            self.width() as usize * 2
        }
    }
}

pub struct JpegInfo {
    size: Offset,
    mcu_height: i16,
}

impl JpegInfo {
    /// Parses a baseline JPEG header and returns the image geometry.
    ///
    /// This is the only validation a host-supplied homescreen gets before the
    /// hardware decoder is pointed at the very same bytes, so the two must
    /// agree on what the image is. A stream that this parser and the decoder
    /// read differently is a crafted input, not a picture, and the strictness
    /// here exists to deny that difference rather than to be permissive.
    pub fn parse(image: BinaryData) -> Option<Self> {
        // Second byte of each two-byte marker code.
        const SOI: u8 = 0xD8;
        const EOI: u8 = 0xD9;
        const SOF0: u8 = 0xC0;
        const SOS: u8 = 0xDA;
        const DRI: u8 = 0xDD;
        const DQT: u8 = 0xDB;
        const DHT: u8 = 0xC4;
        const COM: u8 = 0xFE;
        const APP0: u8 = 0xE0;
        const APP15: u8 = 0xEF;
        const TEM: u8 = 0x01;
        const RST0: u8 = 0xD0;
        const RST7: u8 = 0xD7;

        // A JPEG stream begins with SOI.
        if image.read_u8(0)? != 0xFF || image.read_u8(1)? != SOI {
            return None;
        }

        let mut ofs: usize = 2;
        let mut result: Option<Self> = None;

        loop {
            // A marker is an 0xFF byte followed by a code that is neither 0x00
            // nor 0xFF.
            //
            // Rejecting fill bytes, since hardware cannot decode them.
            let mut ff_run = 0;
            while image.read_u8(ofs)? == 0xFF {
                ff_run += 1;
                ofs = ofs.checked_add(1)?;
            }
            if ff_run != 1 {
                return None;
            }
            let code = image.read_u8(ofs)?;
            // 0xFF00 is a stuffed data byte, never a marker.
            if code == 0x00 {
                return None;
            }
            ofs = ofs.checked_add(1)?;

            match code {
                SOS => break,

                // Allowed markers
                SOF0 | DQT | DHT | DRI | COM | APP0..=APP15 => (),

                // Everything else is refused.
                _ => return None,
            }

            let len = image.read_u16_be(ofs)? as usize;
            if len < 2 {
                return None;
            }

            match code {
                SOF0 => {
                    if result.is_some() {
                        // A baseline image carries exactly one frame header.
                        return None;
                    }
                    result = Some(Self::parse_frame_header(&image, ofs, len)?);
                }
                DRI if len != 4 => return None,
                _ => (),
            }

            ofs = ofs.checked_add(len)?;
        }

        result
    }

    /// Parses a baseline frame header. `ofs` points at its length field.
    fn parse_frame_header(image: &BinaryData, ofs: usize, len: usize) -> Option<Self> {
        // Lf(2) P(1) Y(2) X(2) Nf(1), then Nf x (Ci(1) HiVi(1) Tqi(1)).
        let precision = image.read_u8(ofs + 2)?;
        let height = image.read_u16_be(ofs + 3)?;
        let width = image.read_u16_be(ofs + 5)?;
        let components = image.read_u8(ofs + 7)?;

        // Baseline is 8-bit, greyscale or YCbCr.
        if precision != 8 || (components != 1 && components != 3) {
            return None;
        }
        if len != 8 + 3 * components as usize {
            return None;
        }
        // Both this type and the hardware decoder hold dimensions as `i16`.
        if width == 0 || height == 0 || width > i16::MAX as u16 || height > i16::MAX as u16 {
            return None;
        }

        let mut mcu_height = 0;
        for i in 0..components as usize {
            let sampling = image.read_u8(ofs + 9 + i * 3)?;
            if i == 0 {
                // The decoders derive the whole MCU geometry from the first
                // component and implement only these layouts. A greyscale
                // image is assumed to use 8x8 MCUs, so it must say so.
                mcu_height = match sampling {
                    0x11 => 8,
                    0x21 if components == 3 => 8,
                    0x22 if components == 3 => 16,
                    _ => return None,
                };
            } else if sampling != 0x11 {
                // Chroma subsampled independently of luma yields a component
                // layout no decoder here supports.
                return None;
            }
        }

        Some(Self {
            size: Offset::new(width as i16, height as i16),
            mcu_height,
        })
    }

    pub fn size(&self) -> Offset {
        self.size
    }

    pub fn width(&self) -> i16 {
        self.size.x
    }

    pub fn height(&self) -> i16 {
        self.size.y
    }

    pub fn mcu_height(&self) -> i16 {
        self.mcu_height
    }
}

pub enum ImageInfo {
    Invalid,
    Toif(ToifInfo),
    Jpeg(JpegInfo),
}

impl ImageInfo {
    pub fn parse(image: BinaryData) -> Self {
        if let Some(info) = ToifInfo::parse(image) {
            Self::Toif(info)
        } else if let Some(info) = JpegInfo::parse(image) {
            Self::Jpeg(info)
        } else {
            Self::Invalid
        }
    }
}
