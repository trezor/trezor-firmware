use crate::{io::BinaryData, ui::geometry::Offset};

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
        if image.read_u8(0)? != b'T' && image.read_u8(1)? != b'O' && image.read_u8(2)? != b'I' {
            return None;
        }

        let format = match image.read_u8(3)? {
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
    pub fn parse(image: BinaryData) -> Option<Self> {
        const M_SOI: u16 = 0xFFD8;
        const M_SOF0: u16 = 0xFFC0;
        const M_DRI: u16 = 0xFFDD;
        const M_RST0: u16 = 0xFFD0;
        const M_RST7: u16 = 0xFFD7;
        const M_SOS: u16 = 0xFFDA;
        const M_EOI: u16 = 0xFFD9;

        let mut result = None;
        let mut ofs = 0;

        while image.read_u16_be(ofs)? != M_SOI {
            ofs += 1;
        }

        loop {
            let marker = image.read_u16_be(ofs)?;

            if (marker & 0xFF00) != 0xFF00 {
                return None;
            }

            ofs += 2;

            ofs += match marker {
                M_SOI => 0,
                M_SOF0 => {
                    let h = image.read_u16_be(ofs + 3)? as i16;
                    let w = image.read_u16_be(ofs + 5)? as i16;
                    // Number of components
                    let nc = image.read_u8(ofs + 7)?;
                    if (nc != 1) && (nc != 3) {
                        return None;
                    }
                    // Sampling factor of the first component
                    let c1 = image.read_u8(ofs + 9)?;
                    if (c1 != 0x11) && (c1 != 0x21) & (c1 != 0x22) {
                        return None;
                    };
                    let mcu_height = (8 * (c1 & 15)) as i16;

                    // We now have all the information we need, but
                    // we will not exit the loop yet until we find the
                    // M_SOS marker. While this does not ensure absolute
                    // correctness, it improves the verification slightly.
                    result = Some(JpegInfo {
                        size: Offset::new(w, h),
                        mcu_height,
                    });

                    image.read_u16_be(ofs)?
                }
                M_DRI => 4,
                M_EOI => return None,
                M_RST0..=M_RST7 => 0,
                M_SOS => break,
                _ => image.read_u16_be(ofs)?,
            } as usize;
        }

        result
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
