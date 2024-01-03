mod en;
#[cfg(feature = "micropython")]
mod export;
mod general;
#[cfg(feature = "micropython")]
mod micropython;

use en::EN_TRANSLATIONS;

use crate::trezorhal::translations::{get_pointer_with_offset, get_translations_blob, PointerData};
use core::str;

const TERMINATE_BYTE: u8 = 0xFF;
const ALIGNMENT_BYTE: u8 = 0x00;
const HEADER_LEN: usize = 256;

/// Translation function for Rust.
pub fn tr(key: &str) -> &'static str {
    translate(key).unwrap_or_default()
}

// TODO: somehow make it a singleton object, so it is loaded just once
// TODO: split it into header.rs, translations.rs and font.rs?
// TODO: --- put the {en,cs,fr}.* files to `languages` dir?
// TODO: not generate fr/cs.rs files not to confuse, rather do .txt?
// TODO: add some tests?

struct TranslationsHeader {
    /// Human readable language identifier (e.g. "cs" of "fr")
    pub language: &'static str,
    /// Version in format {major}.{minor}.{patch}
    pub version: &'static str,
    /// Overall length of the data blob (excluding the header)
    pub data_length: u16,
    /// Length of the translation data
    pub translations_length: u16,
    /// Number of translation items
    pub translations_num: u16,
    /// Hash of the data blob (excluding the header)
    pub data_hash: [u8; 32],
    /// Title to show user before changing the language
    pub change_language_title: &'static str,
    /// Text to show user before changing the language
    pub change_language_prompt: &'static str,
}

impl TranslationsHeader {
    const MAGIC: [u8; 4] = [84, 82, 84, 82]; // b"TRTR"
    const VERSION_LEN: usize = 16;
    const LANG_LEN: usize = 32;
    const DATA_HASH_LEN: usize = 32;
    const CHANGE_LANG_TITLE_LEN: usize = 20;
    const CHANGE_LANG_PROMPT_LEN: usize = 40;
    const SIGNATURE_LEN: usize = 65;

    pub fn from_flash() -> Result<Self, &'static str> {
        let header_data = &get_translations_blob()[..HEADER_LEN];
        Self::from_bytes(header_data)
    }

    pub fn from_bytes(data: &'static [u8]) -> Result<Self, &'static str> {
        if data.len() != HEADER_LEN {
            return Err("Invalid header length");
        }

        let (magic, rest) = data.split_at(4);
        if magic != Self::MAGIC {
            return Err("Invalid header magic");
        }

        let (version, rest) = rest.split_at(Self::VERSION_LEN);
        let version = core::str::from_utf8(version)
            .or(Err("Invalid version string"))?
            .trim_end_matches(0 as char);

        let (language, rest) = rest.split_at(Self::LANG_LEN);
        let language = core::str::from_utf8(language)
            .or(Err("Invalid language string"))?
            .trim_end_matches(0 as char);

        let (data_length_bytes, rest) = rest.split_at(2);
        let data_length = u16::from_le_bytes(
            data_length_bytes
                .try_into()
                .or(Err("Invalid data length bytes"))?,
        );

        let (translations_length_bytes, rest) = rest.split_at(2);
        let translations_length = u16::from_le_bytes(
            translations_length_bytes
                .try_into()
                .or(Err("Invalid translations length bytes"))?,
        );

        let (translations_num_bytes, rest) = rest.split_at(2);
        let translations_num = u16::from_le_bytes(
            translations_num_bytes
                .try_into()
                .or(Err("Invalid translations num bytes"))?,
        );

        let (data_hash, rest) = rest.split_at(Self::DATA_HASH_LEN);
        let data_hash: [u8; 32] = data_hash.try_into().or(Err("Invalid data hash length"))?;

        let (change_language_title, rest) = rest.split_at(Self::CHANGE_LANG_TITLE_LEN);
        let change_language_title = core::str::from_utf8(change_language_title)
            .or(Err("Invalid change_language_title string"))?
            .trim_end_matches(0 as char);

        let (change_language_prompt, rest) = rest.split_at(Self::CHANGE_LANG_PROMPT_LEN);
        let change_language_prompt = core::str::from_utf8(change_language_prompt)
            .or(Err("Invalid change_language_prompt string"))?
            .trim_end_matches(0 as char);

        let non_sig_len = rest.len() as i32 - Self::SIGNATURE_LEN as i32;
        if non_sig_len < 0 {
            return Err("Not enough space for signature");
        }
        let (non_sig_rest, _sig) = rest.split_at(non_sig_len as usize);

        // Rest must be empty bytes
        for byte in non_sig_rest {
            if *byte != 0 {
                return Err("Invalid header data");
            }
        }

        // Signature was already checked in micropython

        Ok(Self {
            language,
            version,
            data_length,
            translations_length,
            translations_num,
            data_hash,
            change_language_title,
            change_language_prompt,
        })
    }

    /// Starting offset for the font data.
    pub fn font_start_offset(&self) -> u16 {
        HEADER_LEN as u16 + self.translations_length
    }

    /// Offset for the last byte of the blob.
    pub fn blob_end_offset(&self) -> u16 {
        HEADER_LEN as u16 + self.data_length
    }

    /// Get the part of the blob dedicated to the translations.
    pub fn get_all_translations_data(&self) -> &'static [u8] {
        let start = HEADER_LEN;
        let end = start + self.translations_length as usize;
        &get_translations_blob()[start..end]
    }

    /// Get the offset table for the translations data.
    pub fn get_translations_table(&self) -> OffsetTableData {
        // Each entry has 2 bytes of offset
        // Connection to a specific translation is carried by the index in the table
        const ENTRY_SIZE: usize = 2;
        let table_len = self.translations_num as usize * ENTRY_SIZE;
        let start = HEADER_LEN;
        let end = start + table_len;
        let table_data = &get_translations_blob()[start..end];

        OffsetTableData {
            offset_table_data: table_data,
            overall_len: self.translations_length,
        }
    }

    /// Get the part of the blob dedicated to the fonts.
    pub fn get_all_font_data(&self) -> &'static [u8] {
        let start = self.font_start_offset() as usize;
        let end = self.blob_end_offset() as usize;
        &get_translations_blob()[start..end]
    }

    pub fn get_font_table(&self) -> OffsetTableData {
        let all_font_data = self.get_all_font_data();
        let data_size = all_font_data.len() as u16;

        let (font_amount_bytes, data) = all_font_data.split_at(2);
        let font_amount = u16::from_le_bytes(unwrap!(font_amount_bytes.try_into()));

        // Each entry has 2 bytes of font-ID and 2 bytes of offset
        const FONT_ENTRY_SIZE: usize = 4;
        let pairs_len = font_amount as usize * FONT_ENTRY_SIZE;
        let pairs_data = &data[..pairs_len];

        OffsetTableData {
            offset_table_data: pairs_data,
            overall_len: data_size,
        }
    }

    pub fn get_font_data_offset(&self, font_offset: u16, len: u16) -> &'static [u8] {
        let start = font_offset as usize;
        let end = start + len as usize;
        &self.get_all_font_data()[start..end]
    }
}

pub struct OffsetTableData {
    /// Offset table raw data
    pub offset_table_data: &'static [u8],
    /// Overall length of the data (used for getting the length of the last
    /// element in the table)
    pub overall_len: u16,
}

/// Get the language name.
fn get_language_name() -> Option<&'static str> {
    TranslationsHeader::from_flash()
        .ok()
        .map(|header| header.language)
}

/// Try to find the translation in flash (for a non-english language).
/// If not found, fallback to english.
fn translate(key: &str) -> Option<&'static str> {
    let mut translation: Option<&'static str> = None;

    if are_there_translations() {
        if let Some(index) = EN_TRANSLATIONS.get_position(key) {
            translation = get_translation_by_index(index);
        }
    }

    if translation.is_none() {
        translation = EN_TRANSLATIONS.get_text(key);
    }

    translation
}

/// Quickly checks whether there are some valid translations data
fn are_there_translations() -> bool {
    get_translations_blob()[0] != TERMINATE_BYTE
}

/// Returns the translation at the given index.
fn get_translation_by_index(index: usize) -> Option<&'static str> {
    // TODO: do not use unwrap, probably return None in case of Err?
    // --- not to introduce panic in case of corrupted data in flash
    let header = unwrap!(TranslationsHeader::from_flash());
    let translations_table = header.get_translations_table();

    let offsets = read_u16_list(translations_table.offset_table_data);

    // The index is out of bounds.
    // May happen when new firmware is using older translations and the string
    // is not defined yet.
    // Fallback to english.
    if index > offsets.len() {
        return None;
    }

    // Identifying where the string starts.
    let start_offset = offsets[index];

    // In case the string is last, we may need to strip the alignment bytes
    let mut strip_alignment_bytes = false;

    // Getting the data length - difference between the current offset and the next
    // one.
    let len = if index == offsets.len() - 1 {
        // The last element in the table
        strip_alignment_bytes = true;
        translations_table.overall_len - start_offset
    } else {
        offsets[index + 1] - start_offset
    };

    // The string is not defined in the blob.
    // May happen when old firmware is using newer translations and the string
    // was deleted in the newer version.
    // Fallback to english.
    if len == 0 {
        return None;
    }

    let start = start_offset as usize;
    let mut end = start + len as usize;
    let translations_data = header.get_all_translations_data();
    if strip_alignment_bytes {
        // Strip possible alignment bytes at the end
        while translations_data[end - 1] == ALIGNMENT_BYTE {
            end -= 1;
        }
    }
    let data = &translations_data[start..end];
    str::from_utf8(data).ok()
}

/// Given blob data returns a list of (u16, u16) values.
fn read_u16_pairs_list(bytes: &'static [u8]) -> &'static [(u16, u16)] {
    let (prefix, data, suffix) = unsafe { bytes.align_to::<(u16, u16)>() };
    if !prefix.is_empty() || !suffix.is_empty() {
        return &[];
    }
    data
}

/// Given blob data returns a list of u16 values.
fn read_u16_list(bytes: &'static [u8]) -> &'static [u16] {
    let (prefix, data, suffix) = unsafe { bytes.align_to::<u16>() };
    if !prefix.is_empty() || !suffix.is_empty() {
        return &[];
    }
    data
}

pub struct OffsetLen {
    pub offset: u16,
    pub len: u16,
}

/// Information about specific font - where it starts and how long it is
fn get_font_offset_from_id(font_id: u16) -> Option<OffsetLen> {
    // TODO: do not use unwrap?
    let font_table = unwrap!(TranslationsHeader::from_flash()).get_font_table();
    match_first_u16_pair(
        font_id,
        font_table.offset_table_data,
        font_table.overall_len,
    )
}

/// Returns the offset and length of the u16 pair whose first element matches
/// `code_id`.
fn match_first_u16_pair(
    code_id: u16,
    pairs_data: &'static [u8],
    overall_len: u16,
) -> Option<OffsetLen> {
    // To get the length of the font, need to read the offset of the next font
    let mut font_offset: Option<u16> = None;
    let mut next_offset: Option<u16> = None;

    for &(code, offset) in read_u16_pairs_list(pairs_data) {
        if code == code_id {
            font_offset = Some(offset);
        } else if font_offset.is_some() {
            next_offset = Some(offset);
            break;
        }
    }

    if let Some(offset) = font_offset {
        // When our font was last, there is no next offset - use the data size
        let next = next_offset.unwrap_or(overall_len);
        let len = next - offset;
        return Some(OffsetLen { offset, len });
    }

    None
}

// Get information about a given glyph with a given font-offset
fn get_glyph_data(char_code: u16, font_offset: u16, font_len: u16) -> Option<OffsetLen> {
    // TODO: do not use unwrap?
    let font_data =
        unwrap!(TranslationsHeader::from_flash()).get_font_data_offset(font_offset, font_len);
    let data_size = font_data.len() as u16;

    let (glyph_amount_bytes, data) = font_data.split_at(2);
    let glyph_amount = u16::from_le_bytes(unwrap!(glyph_amount_bytes.try_into()));

    // Each entry has 2 bytes of glyph-code and 2 bytes of offset
    const GLYPH_ENTRY_SIZE: usize = 4;
    let pairs_len = glyph_amount as usize * GLYPH_ENTRY_SIZE;
    let pairs_data = &data[..pairs_len];

    match_first_u16_pair(char_code, pairs_data, data_size)
}

/// Get information about the glyph in the given font.
/// First finding out the offset of the font within the translations data.
/// Then finding out the offset of the glyph within the font.
/// Returning the absolute offset of the glyph within the translations data -
/// together with its length.
fn get_glyph_font_data(char_code: u16, font_id: u16) -> Option<OffsetLen> {
    if !are_there_translations() {
        return None;
    }

    if let Some(font_offset) = get_font_offset_from_id(font_id) {
        if let Some(glyph_data) = get_glyph_data(char_code, font_offset.offset, font_offset.len) {
            // TODO: do not use unwrap?
            let font_start_offset = unwrap!(TranslationsHeader::from_flash()).font_start_offset();
            let final_offset = font_start_offset + font_offset.offset + glyph_data.offset;
            return Some(OffsetLen {
                offset: final_offset,
                len: glyph_data.len,
            });
        }
    }
    None
}

#[no_mangle]
pub extern "C" fn get_utf8_glyph(char_code: cty::uint16_t, font: cty::c_int) -> PointerData {
    // C will send a negative number
    let font_abs = font.unsigned_abs() as u16;

    if let Some(glyph_data) = get_glyph_font_data(char_code, font_abs) {
        return get_pointer_with_offset(glyph_data.offset, glyph_data.len);
    }

    PointerData {
        ptr: core::ptr::null(),
        len: 0,
    }
}
