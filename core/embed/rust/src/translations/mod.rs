mod flash;
mod generated;
#[cfg(feature = "micropython")]
mod micropython;
mod translated_string;

pub use translated_string::TranslatedString as TR;

use crate::{error::Error, io::InputStream};
use core::{ptr::null, str};

const HEADER_LEN: usize = 256;

// TODO: somehow make it a singleton object, so it is loaded just once
// TODO: split it into header.rs, translations.rs and font.rs?
// TODO: --- put the {en,cs,fr}.* files to `languages` dir?
// TODO: not generate fr/cs.rs files not to confuse, rather do .txt?
// TODO: add some tests?

#[repr(packed)]
struct OffsetEntry {
    pub id: u16,
    pub offset: u16,
}

struct Table<'a> {
    offsets: &'a [OffsetEntry],
    data: &'a [u8],
}

impl<'a> Table<'a> {
    pub fn new(data: &'a [u8]) -> Result<Self, Error> {
        let mut reader = crate::io::InputStream::new(data);
        let count = reader.read_u16_le()?;
        // The offsets table is (count + 1) entries long, the last entry is a sentinel.
        let offsets_data =
            reader.read((count + 1) as usize * core::mem::size_of::<OffsetEntry>())?;
        // SAFETY: OffsetEntry is repr(packed) of two u16 values, so any four bytes are
        // a valid OffsetEntry value.
        let (_prefix, offsets, _suffix) = unsafe { offsets_data.align_to::<OffsetEntry>() };
        if !_prefix.is_empty() || !_suffix.is_empty() {
            return Err(value_error!("Invalid offsets table"));
        }

        Ok(Self {
            offsets,
            data: reader.rest(),
        })
    }

    pub fn get(&self, id: u16) -> Option<&'a [u8]> {
        self.offsets
            .iter()
            .position(|it| it.id == id)
            .and_then(|idx| {
                let start = self.offsets[idx].offset as usize;
                let end = self.offsets[idx + 1].offset as usize;
                self.data.get(start..end)
            })
    }
}

struct Translations<'a> {
    pub header: TranslationsHeader<'a>,
    translations: &'a [u8],
    translation_offsets: &'a [u16],
    fonts: Table<'a>,
}

impl<'a> Translations<'a> {
    pub fn new(blob: &'a [u8]) -> Result<Self, Error> {
        let header = TranslationsHeader::parse(&blob[..HEADER_LEN])?;
        let data_len = header.data_length as usize;
        if blob.len() < HEADER_LEN + data_len {
            return Err(Error::EOFError);
        }
        let data = &blob[HEADER_LEN..HEADER_LEN + data_len];
        if header.translations_length > data.len() as u16 {
            return Err(value_error!("Invalid translations length field"));
        }

        let translations = &data[..header.translations_length as usize];
        // length of offsets table is (count + 1) entries, the last one is a sentinel
        let table_len = (header.translations_count + 1) as usize * core::mem::size_of::<u16>();
        if table_len > translations.len() {
            return Err(value_error!("Invalid translations table"));
        }
        // SAFETY: any bytes are valid u16 values, so casting any data to
        // a sequence of u16 values is safe.
        let (_prefix, translation_offsets, _suffix) =
            unsafe { data[..table_len].align_to::<u16>() };
        if !_prefix.is_empty() || !_suffix.is_empty() {
            return Err(value_error!("Invalid translations table"));
        }

        let fonts_data = &data[header.translations_length as usize..];

        Ok(Self {
            header,
            translations,
            translation_offsets,
            fonts: Table::new(fonts_data)?,
        })
    }

    /// Returns the translation at the given index.
    pub fn translation(&self, index: usize) -> Option<&str> {
        if index >= self.translation_offsets.len() + 1 {
            // The index is out of bounds.
            // May happen when new firmware is using older translations and the string
            // is not defined yet.
            // Fallback to english.
            return None;
        }

        let start_offset = self.translation_offsets[index] as usize;
        let end_offset = self.translation_offsets[index + 1] as usize;

        // Construct the relevant slice
        let string = &self.translations[start_offset..end_offset];

        if string.is_empty() {
            // The string is not defined in the blob.
            // May happen when old firmware is using newer translations and the string
            // was deleted in the newer version.
            // Fallback to english.
            return None;
        }

        str::from_utf8(string).ok()
    }

    pub fn font(&'a self, index: u16) -> Option<Table<'a>> {
        self.fonts.get(index).and_then(|data| Table::new(data).ok())
    }
}

struct TranslationsHeader<'a> {
    /// Human readable language identifier (e.g. "cs" of "fr")
    pub language: &'a str,
    /// 4 bytes of version (major, minor, patch, build)
    pub version: [u8; 4],
    /// Overall length of the data blob (excluding the header)
    pub data_length: u16,
    /// Length of the header
    pub header_length: u16,
    /// Length of the translation data
    pub translations_length: u16,
    /// Number of translation items
    pub translations_count: u16,
    /// Hash of the data blob (excluding the header)
    pub data_hash: [u8; 32],
    /// Title to show user before changing the language
    pub change_language_title: &'a str,
    /// Text to show user before changing the language
    pub change_language_prompt: &'a str,
}

impl<'a> TranslationsHeader<'a> {
    const MAGIC: &'static [u8] = b"TRTR00";
    const VERSION_LEN: usize = 16;
    const LANG_LEN: usize = 32;
    const DATA_HASH_LEN: usize = 32;
    const CHANGE_LANG_TITLE_LEN: usize = 20;
    const CHANGE_LANG_PROMPT_LEN: usize = 40;
    const SIGNATURE_LEN: usize = 65;

    fn read_fixedsize_str<'b, 'c: 'b>(reader: &'b mut InputStream<'c>, len: usize) -> Result<&'c str, Error> {
        let bytes = reader.read(len)?;
        let string = core::str::from_utf8(bytes)
            .map_err(|_| value_error!("Invalid string"))?
            .trim_end_matches(0 as char);
        Ok(string)
    }

    pub fn parse(data: &'a [u8]) -> Result<Self, Error> {
        if data.len() != HEADER_LEN {
            return Err(value_error!("Invalid header length"));
        }

        let mut reader = crate::io::InputStream::new(data);

        let magic = reader.read(Self::MAGIC.len())?;
        if magic != Self::MAGIC {
            return Err(value_error!("Invalid header magic"));
        }

        let version_bytes = reader.read(4)?;
        let version = unwrap!(version_bytes.try_into());
        let language = Self::read_fixedsize_str(&mut reader, Self::LANG_LEN)?;
        let data_length = reader.read_u16_le()?;
        let translations_length = reader.read_u16_le()?;
        let translations_count = reader.read_u16_le()?;
        let data_hash = unwrap!(reader.read(32)?.try_into());
        let change_language_title =
            Self::read_fixedsize_str(&mut reader, Self::CHANGE_LANG_TITLE_LEN)?;
        let change_language_prompt =
            Self::read_fixedsize_str(&mut reader, Self::CHANGE_LANG_PROMPT_LEN)?;

        if translations_length > data_length {
            return Err(value_error!("Invalid translations length field"));
        }

        let trailing_data = reader.rest();
        if trailing_data.len() < Self::SIGNATURE_LEN {
            return Err(value_error!("Invalid header signature"));
        }

        // TODO check signature

        Ok(Self {
            language,
            version,
            data_length,
            header_length: 0,
            translations_length,
            translations_count,
            data_hash,
            change_language_title,
            change_language_prompt,
        })
    }
}

#[no_mangle]
pub unsafe extern "C" fn get_utf8_glyph(codepoint: cty::uint16_t, font: cty::c_int) -> *const u8 {
    // C will send a negative number
    let font_abs = font.unsigned_abs() as u16;

    // SAFETY:
    // We rely on the fact that the caller (`display_text_render` and friends) uses
    // and discards this data immediately.
    let Some(tr) = (unsafe { flash::get() }) else {
        return null();
    };
    if let Some(glyph) = tr.font(font_abs).and_then(|t| t.get(codepoint)) {
        glyph.as_ptr()
    } else {
        null()
    }
}
