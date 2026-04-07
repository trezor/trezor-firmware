use core::{mem, str};

use heapless::Vec;

use crate::{
    crypto::{cosi, ed25519, merkle::merkle_root, sha256},
    error::{value_error, Error},
    io::InputStream,
};

use super::{public_keys, translated_string::TranslatedString};

pub const MAX_HEADER_LEN: u16 = 1024;
pub const EMPTY_BYTE: u8 = 0xFF;
const SENTINEL_ID: u16 = 0xFFFF;

const SIGNATURE_THRESHOLD: u8 = 2;

// Maximum padding at the end of an offsets table (typically for alignment
// purposes). We allow at most 3 for alignment 4. In practice right now this
// should be max 1.
const MAX_TABLE_PADDING: usize = 3;

const INVALID_TRANSLATIONS_BLOB: Error = value_error!(c"Invalid translations blob");

#[repr(C, packed)]
struct OffsetEntry {
    pub id: u16,
    pub offset: u16,
}

pub struct Table<'a> {
    offsets: &'a [OffsetEntry],
    data: &'a [u8],
}

fn validate_offset_table(
    data_len: usize,
    mut iter: impl Iterator<Item = u16>,
) -> Result<(), Error> {
    // every offset table must have at least the sentinel
    let mut prev = iter.next().ok_or(INVALID_TRANSLATIONS_BLOB)?;
    if prev != 0 {
        // first offset must always be 0 (even as a sentinel, indicating no data)
        return Err(INVALID_TRANSLATIONS_BLOB);
    }
    for next in iter {
        // offsets must be in ascending order
        if prev > next {
            return Err(INVALID_TRANSLATIONS_BLOB);
        }
        prev = next;
    }
    // sentinel needs to be at least data_len - MAX_TABLE_PADDING, and at most
    // data_len
    let sentinel: usize = prev.into();
    if sentinel < data_len - MAX_TABLE_PADDING || sentinel > data_len {
        return Err(INVALID_TRANSLATIONS_BLOB);
    }
    Ok(())
}

impl<'a> Table<'a> {
    pub fn new(mut reader: InputStream<'a>) -> Result<Self, Error> {
        let count = reader.read_u16_le()?;
        // The offsets table is (count + 1) entries long, the last entry is a sentinel.
        let offsets_len: usize = (count + 1).into();
        let offsets_data = reader.read(offsets_len * mem::size_of::<OffsetEntry>())?;
        // SAFETY: OffsetEntry is repr(packed) of two u16 values, so any four bytes are
        // a valid OffsetEntry value.
        let (_prefix, offsets, _suffix) = unsafe { offsets_data.align_to::<OffsetEntry>() };
        if !_prefix.is_empty() || !_suffix.is_empty() {
            return Err(INVALID_TRANSLATIONS_BLOB);
        }

        Ok(Self {
            offsets,
            data: reader.rest(),
        })
    }

    pub fn validate(&self) -> Result<(), Error> {
        validate_offset_table(self.data.len(), self.offsets.iter().map(|it| it.offset))?;
        if !matches!(
            self.offsets.iter().last().map(|it| it.id),
            Some(SENTINEL_ID)
        ) {
            return Err(INVALID_TRANSLATIONS_BLOB);
        }
        // check that the ids are sorted
        let Some(first_entry) = self.offsets.first() else {
            // empty table is sorted
            return Ok(());
        };
        let mut prev_id = first_entry.id;
        for entry in self.offsets.iter().skip(1) {
            if entry.id <= prev_id {
                return Err(INVALID_TRANSLATIONS_BLOB);
            }
            prev_id = entry.id;
        }
        Ok(())
    }

    pub fn get(&self, id: u16) -> Option<&'a [u8]> {
        self.offsets
            .binary_search_by_key(&id, |it| it.id)
            .ok()
            .and_then(|idx| {
                let start = self.offsets[idx].offset.into();
                let end = self.offsets[idx + 1].offset.into();
                self.data.get(start..end)
            })
    }

    pub fn iter(&self) -> impl Iterator<Item = (u16, &'a [u8])> + '_ {
        let mut prev_offset = 0usize;
        self.offsets.iter().skip(1).map(move |entry| {
            let start = prev_offset;
            let end = entry.offset.into();
            prev_offset = end;
            (entry.id, &self.data[start..end])
        })
    }
}

pub(super) struct TranslationStringsChunk<'a> {
    strings: &'a str,
    offsets: &'a [u16],
}

impl<'a> TranslationStringsChunk<'a> {
    fn parse_from(mut reader: InputStream<'a>) -> Result<Self, Error> {
        let count: usize = reader.read_u16_le()?.into();
        let offsets_bytes = reader.read((count + 1) * mem::size_of::<u16>())?;
        // SAFETY: any bytes are valid u16 values, so casting any data to
        // a sequence of u16 values is safe.
        let (_prefix, offsets, _suffix) = unsafe { offsets_bytes.align_to::<u16>() };
        if !_prefix.is_empty() || !_suffix.is_empty() {
            return Err(INVALID_TRANSLATIONS_BLOB);
        }
        let strings = str::from_utf8(reader.rest()).map_err(|_| INVALID_TRANSLATIONS_BLOB)?;
        validate_offset_table(strings.len(), offsets.iter().copied())?;
        Ok(Self { strings, offsets })
    }

    const fn len(&self) -> usize {
        // The last entry is a sentinel
        self.offsets.len() - 1
    }

    pub fn get(&self, index: usize) -> Option<&'a str> {
        if index >= self.len() {
            return None;
        }
        let start_offset = self.offsets[index].into();
        let end_offset = self.offsets[index + 1].into();
        // Construct the relevant slice
        Some(&self.strings[start_offset..end_offset])
    }
}

const MAX_TRANSLATION_CHUNKS: usize = 4;

pub struct Translations<'a> {
    header: TranslationsHeader<'a>,
    chunks: Vec<TranslationStringsChunk<'a>, MAX_TRANSLATION_CHUNKS>,
    fonts: Table<'a>,
}

fn read_u16_prefixed_block<'a>(reader: &mut InputStream<'a>) -> Result<InputStream<'a>, Error> {
    let len = reader.read_u16_le()?;
    reader.read_stream(len.into())
}

impl<'a> Translations<'a> {
    pub fn new(blob: &'a [u8]) -> Result<Self, Error> {
        let mut blob_reader = InputStream::new(blob);

        let (header, payload_reader) = TranslationsHeader::parse_from(&mut blob_reader)?;

        // validate that the trailing bytes, if any, are empty
        let remaining = blob_reader.rest();
        if !remaining.iter().all(|&b| b == EMPTY_BYTE) {
            // TODO optimize to quadwords?
            return Err(value_error!(c"Trailing data in translations blob"));
        }

        let payload_bytes = payload_reader.rest();

        let payload_digest = sha256::digest(payload_bytes);
        if payload_digest != header.data_hash {
            return Err(INVALID_TRANSLATIONS_BLOB);
        }

        let mut payload_reader = InputStream::new(payload_bytes);

        // construct translations data
        let chunks = header.parse_translation_chunks(&mut payload_reader)?;
        let fonts_reader = read_u16_prefixed_block(&mut payload_reader)?;

        if payload_reader.remaining() > 0 {
            return Err(INVALID_TRANSLATIONS_BLOB);
        }

        // construct and validate font table
        let fonts = Table::new(fonts_reader)?;
        fonts.validate()?;
        for (_, font_data) in fonts.iter() {
            let reader = InputStream::new(font_data);
            let font_table = Table::new(reader)?;
            font_table.validate()?;
        }
        Ok(Self {
            header,
            chunks,
            fonts,
        })
    }

    /// Returns the translation at the given index.
    ///
    /// SAFETY: Do not mess with the lifetimes in this signature.
    ///
    /// The lifetimes are a useful lie that bind the lifetime of the returned
    /// string not to the underlying data, but to the _reference_ to the
    /// translations object. This is to facilitate safe interface to
    /// flash-based translations. See docs for `flash::get` for details.
    #[allow(clippy::needless_lifetimes)]
    pub fn translation<'b>(&'b self, mut index: usize) -> Option<&'b str> {
        for chunk in &self.chunks {
            match chunk.get(index) {
                Some(string) => {
                    if string.is_empty() {
                        // The string is not defined in the blob.
                        // May happen when old firmware is using newer translations and the string
                        // was deleted in the newer version.
                        // Fallback to english.
                        return None;
                    }
                    return Some(string);
                }
                None => {
                    index -= chunk.len();
                    continue; // search next chunks
                }
            }
        }
        None
    }

    /// Returns the font table at the given index.
    ///
    /// SAFETY: Do not mess with the lifetimes in this signature.
    ///
    /// The lifetimes are a useful lie that bind the lifetime of the returned
    /// string not to the underlying data, but to the _reference_ to the
    /// translations object. This is to facilitate safe interface to
    /// flash-based translations. See docs for `flash::get` for details.
    #[allow(clippy::needless_lifetimes)]
    fn font<'b>(&'b self, index: u16) -> Option<Table<'b>> {
        self.fonts
            .get(index)
            .and_then(|data| Table::new(InputStream::new(data)).ok())
    }

    /// Returns the header of the translations blob.
    ///
    /// SAFETY: Do not mess with the lifetimes in this signature.
    ///
    /// The lifetimes are a useful lie that bind the lifetime of the returned
    /// string not to the underlying data, but to the _reference_ to the
    /// translations object. This is to facilitate safe interface to
    /// flash-based translations. See docs for `flash::get` for details.
    #[allow(clippy::needless_lifetimes)]
    pub fn header<'b>(&'b self) -> &'b TranslationsHeader<'b> {
        &self.header
    }

    /// Returns a byte slice of the glyph data for the given UTF-8 codepoint in
    /// the specified font.
    ///
    /// SAFETY: Do not mess with the lifetimes in this signature.
    ///
    /// The lifetimes are a useful lie that bind the lifetime of the returned
    /// string not to the underlying data, but to the _reference_ to the
    /// translations object. This is to facilitate safe interface to
    /// flash-based translations. See docs for `flash::get` for details.
    #[allow(clippy::needless_lifetimes)]
    pub fn get_utf8_glyph<'b>(&'b self, codepoint: u16, font_index: u16) -> Option<&'b [u8]> {
        self.font(font_index).and_then(|t| t.get(codepoint))
    }
}

pub struct TranslationsHeader<'a> {
    /// Blob magic
    blob_magic: BlobMagic,
    /// Raw content of the header, for signature verification
    pub header_bytes: &'a [u8],
    /// BCP 47 language tag (cs-CZ, en-US, ...)
    pub language: &'a str,
    /// 4 bytes of version (major, minor, patch, build)
    pub version: [u8; 4],
    /// Length of the raw data, i.e. translations section + fonts section
    pub data_len: usize,
    /// Hash of the data blob (excluding the header)
    pub data_hash: sha256::Digest,
    /// Merkle proof items
    pub merkle_proof: &'a [sha256::Digest],
    /// CoSi signature
    pub signature: cosi::Signature,
    /// Expected total length of the blob
    pub total_len: usize,
}

fn read_fixedsize_str<'a>(reader: &mut InputStream<'a>, len: usize) -> Result<&'a str, Error> {
    let bytes = reader.read(len)?;
    let find_zero = bytes.iter().position(|&b| b == 0).unwrap_or(len);
    let bytes_trimmed = &bytes[..find_zero];
    core::str::from_utf8(bytes_trimmed).map_err(|_| INVALID_TRANSLATIONS_BLOB)
}

enum BlobMagic {
    V0,
    V1,
}

impl BlobMagic {
    fn parse_length(&self, reader: &mut InputStream<'_>) -> Result<usize, Error> {
        Ok(match self {
            Self::V0 => reader.read_u16_le()?.into(),
            Self::V1 => reader
                .read_u32_le()?
                .try_into() // can fail only on 16-bit system
                .map_err(|_| Error::OutOfRange)?,
        })
    }
}

struct ContainerPrefix {
    blob_magic: BlobMagic,
    container_length: usize,
    prefix_length: usize,
}

impl ContainerPrefix {
    fn parse_from(reader: &mut InputStream<'_>) -> Result<Self, Error> {
        let offset = reader.tell();
        let data = reader.read(6)?;
        let blob_magic = match data {
            b"TRTR00" => BlobMagic::V0,
            b"TRTR01" => BlobMagic::V1,
            _ => return Err(Error::ValueError(c"Unknown blob magic")),
        };
        let container_length = blob_magic.parse_length(reader)?;
        let prefix_length = reader.tell() - offset;
        Ok(Self {
            blob_magic,
            container_length,
            prefix_length,
        })
    }
}

impl<'a> TranslationsHeader<'a> {
    const HEADER_MAGIC: &'static [u8] = b"TR";
    const LANGUAGE_TAG_LEN: usize = 8;

    /// Parse a translations header out of a stream.
    ///
    /// The returned tuple consists of:
    /// (a) the parsed header and
    /// (b) reader of the payload section of the translations blob.
    /// The caller can use the returned reader to parse the payload.
    ///
    /// The input stream is positioned at the end of the translations blob (or
    /// at the end of stream, whichever comes sooner). The caller can use this
    /// to verify that there is no unexpected trailing data in the input
    /// stream. (Also, you cannot make a mistake and read the payload out of
    /// the input stream).
    pub fn parse_from(reader: &mut InputStream<'a>) -> Result<(Self, InputStream<'a>), Error> {
        //
        // 1. parse outer container
        //

        // read the blob magic and length of contained data
        let prefix = ContainerPrefix::parse_from(reader)?;

        // continue working on the contained data (i.e., read beyond the bounds of
        // container_length will result in EOF).
        let mut reader = reader.read_stream(prefix.container_length.min(reader.remaining()))?;

        //
        // 2. parse the header section
        //
        let header_bytes = read_u16_prefixed_block(&mut reader)?.rest();

        let mut header_reader = InputStream::new(header_bytes);

        let magic = header_reader.read(Self::HEADER_MAGIC.len())?;
        if magic != Self::HEADER_MAGIC {
            return Err(INVALID_TRANSLATIONS_BLOB);
        }

        let language = read_fixedsize_str(&mut header_reader, Self::LANGUAGE_TAG_LEN)?;
        if language.is_empty() {
            return Err(INVALID_TRANSLATIONS_BLOB);
        }

        let model = read_fixedsize_str(&mut header_reader, 4)?;
        if model != crate::trezorhal::model::INTERNAL_NAME {
            return Err(value_error!(c"Wrong Trezor model"));
        }

        let version_bytes = header_reader.read(4)?;
        let version = unwrap!(version_bytes.try_into());

        let data_len: usize = prefix.blob_magic.parse_length(&mut header_reader)?;
        let data_hash: sha256::Digest =
            unwrap!(header_reader.read(sha256::DIGEST_SIZE)?.try_into());

        // ignore the rest of the header reader - this allows older firmware to
        // understand newer header if there are only added items
        _ = header_reader.rest();

        //
        // 3. parse the proof section
        //
        let mut proof_reader = read_u16_prefixed_block(&mut reader)?;
        let proof_count: usize = proof_reader.read_byte()?.into();
        let proof_length = proof_count * sha256::DIGEST_SIZE;
        let proof_bytes = proof_reader.read(proof_length)?;

        // create a list of the proof items
        // SAFETY: sha256::Digest is a plain array of u8, so any bytes are valid
        let (_prefix, merkle_proof, _suffix) = unsafe { proof_bytes.align_to::<sha256::Digest>() };
        if !_prefix.is_empty() || !_suffix.is_empty() {
            return Err(INVALID_TRANSLATIONS_BLOB);
        }
        let signature = cosi::Signature::new(
            proof_reader.read_byte()?,
            unwrap!(proof_reader.read(ed25519::SIGNATURE_SIZE)?.try_into()),
        );

        // check that there is no trailing data in the proof section
        if proof_reader.remaining() > 0 {
            return Err(INVALID_TRANSLATIONS_BLOB);
        }

        // check that the declared data section length matches the container size
        if prefix.container_length - reader.tell() != data_len {
            return Err(INVALID_TRANSLATIONS_BLOB);
        }

        let new = Self {
            header_bytes,
            language,
            version,
            data_len,
            data_hash,
            merkle_proof,
            signature,
            total_len: prefix.container_length + prefix.prefix_length,
            blob_magic: prefix.blob_magic,
        };
        new.verify()?;
        Ok((new, reader))
    }

    fn parse_translation_chunks(
        &self,
        reader: &mut InputStream<'a>,
    ) -> Result<Vec<TranslationStringsChunk<'a>, MAX_TRANSLATION_CHUNKS>, Error> {
        let chunks_count = match self.blob_magic {
            BlobMagic::V0 => 1,
            BlobMagic::V1 => reader.read_u16_le()?.into(),
        };
        if chunks_count > MAX_TRANSLATION_CHUNKS {
            return Err(Error::OutOfRange);
        }
        let mut chunks = Vec::new();
        for _ in 0..chunks_count {
            let chunk_reader = read_u16_prefixed_block(reader)?;
            let chunk = TranslationStringsChunk::parse_from(chunk_reader)?;
            chunks.push(chunk).map_err(|_| INVALID_TRANSLATIONS_BLOB)?;
        }
        Ok(chunks)
    }

    fn verify_with_keys(&self, public_keys: &[ed25519::PublicKey]) -> Result<(), Error> {
        let merkle_root = merkle_root(self.header_bytes, self.merkle_proof);
        Ok(cosi::verify(
            SIGNATURE_THRESHOLD,
            &merkle_root,
            public_keys,
            &self.signature,
        )?)
    }

    pub fn verify(&self) -> Result<(), Error> {
        #[allow(unused_mut)]
        let mut result = self.verify_with_keys(&public_keys::PUBLIC_KEYS);

        #[cfg(feature = "dev_keys")]
        if result.is_err() {
            // allow development keys
            result = self.verify_with_keys(&public_keys::PUBLIC_KEYS_DEVEL);
        }

        result
    }
}

// The constants below are generated by `translated_string.rs.mako` template.
pub const ENGLISH_CHUNK: TranslationStringsChunk<'static> = TranslationStringsChunk {
    strings: TranslatedString::ENGLISH_STRINGS,
    offsets: TranslatedString::ENGLISH_OFFSETS,
};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_english() {
        // Make sure English chunk was generated correctly.
        validate_offset_table(
            ENGLISH_CHUNK.strings.len(),
            ENGLISH_CHUNK.offsets.iter().copied(),
        )
        .expect("offsets are valid");
        assert!(ENGLISH_CHUNK.strings.is_ascii());
        for i in 0..ENGLISH_CHUNK.len() {
            ENGLISH_CHUNK.get(i).expect("valid index");
        }
        assert_eq!(ENGLISH_CHUNK.get(ENGLISH_CHUNK.len()), None);
    }
}
