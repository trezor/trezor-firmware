use core::{mem, str};

use crate::{
    crypto::{cosi, ed25519, merkle::merkle_root, sha256},
    error::{value_error, Error},
    io::InputStream,
};

use super::public_keys;

pub const MAX_HEADER_LEN: u16 = 1024;
pub const EMPTY_BYTE: u8 = 0xFF;
const SENTINEL_ID: u16 = 0xFFFF;

const SIGNATURE_THRESHOLD: u8 = 2;

// Maximum padding at the end of an offsets table (typically for alignment
// purposes). We allow at most 3 for alignment 4. In practice right now this
// should be max 1.
const MAX_TABLE_PADDING: usize = 3;

const INVALID_TRANSLATIONS_BLOB: Error = value_error!(c"Invalid translations blob");

#[repr(packed)]
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
    let sentinel = prev as usize;
    if sentinel < data_len - MAX_TABLE_PADDING || sentinel > data_len {
        return Err(INVALID_TRANSLATIONS_BLOB);
    }
    Ok(())
}

impl<'a> Table<'a> {
    pub fn new(mut reader: InputStream<'a>) -> Result<Self, Error> {
        let count = reader.read_u16_le()?;
        // The offsets table is (count + 1) entries long, the last entry is a sentinel.
        let offsets_data = reader.read((count + 1) as usize * mem::size_of::<OffsetEntry>())?;
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
                let start = self.offsets[idx].offset as usize;
                let end = self.offsets[idx + 1].offset as usize;
                self.data.get(start..end)
            })
    }

    pub fn iter(&self) -> impl Iterator<Item = (u16, &'a [u8])> + '_ {
        let mut prev_offset = 0usize;
        self.offsets.iter().skip(1).map(move |entry| {
            let start = prev_offset;
            let end = entry.offset as usize;
            prev_offset = end;
            (entry.id, &self.data[start..end])
        })
    }
}

pub struct Translations<'a> {
    header: TranslationsHeader<'a>,
    translations: &'a [u8],
    translations_offsets: &'a [u16],
    fonts: Table<'a>,
}

fn read_u16_prefixed_block<'a>(reader: &mut InputStream<'a>) -> Result<InputStream<'a>, Error> {
    let len = reader.read_u16_le()? as usize;
    reader.read_stream(len)
}

impl<'a> Translations<'a> {
    const MAGIC: &'static [u8] = b"TRTR00";

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

        let mut translations_reader = read_u16_prefixed_block(&mut payload_reader)?;
        let fonts_reader = read_u16_prefixed_block(&mut payload_reader)?;

        if payload_reader.remaining() > 0 {
            return Err(INVALID_TRANSLATIONS_BLOB);
        }

        // construct translations data
        let translations_count = translations_reader.read_u16_le()? as usize;
        let translations_offsets_bytes =
            translations_reader.read((translations_count + 1) * mem::size_of::<u16>())?;
        // SAFETY: any bytes are valid u16 values, so casting any data to
        // a sequence of u16 values is safe.
        let (_prefix, translations_offsets, _suffix) =
            unsafe { translations_offsets_bytes.align_to::<u16>() };
        if !_prefix.is_empty() || !_suffix.is_empty() {
            return Err(INVALID_TRANSLATIONS_BLOB);
        }
        let translations = translations_reader.rest();
        validate_offset_table(translations.len(), translations_offsets.iter().copied())?;

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
            translations,
            translations_offsets,
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
    pub fn translation<'b>(&'b self, index: usize) -> Option<&'b str> {
        if index + 1 >= self.translations_offsets.len() {
            // The index is out of bounds.
            // (The last entry is a sentinel, so the last valid index is len - 2)
            // May happen when new firmware is using older translations and the string
            // is not defined yet.
            // Fallback to english.
            return None;
        }

        let start_offset = self.translations_offsets[index] as usize;
        let end_offset = self.translations_offsets[index + 1] as usize;

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

    /// Returns the font table at the given index.
    ///
    /// SAFETY: Do not mess with the lifetimes in this signature.
    ///
    /// The lifetimes are a useful lie that bind the lifetime of the returned
    /// string not to the underlying data, but to the _reference_ to the
    /// translations object. This is to facilitate safe interface to
    /// flash-based translations. See docs for `flash::get` for details.
    #[allow(clippy::needless_lifetimes)]
    pub fn font<'b>(&'b self, index: u16) -> Option<Table<'b>> {
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
}

pub struct TranslationsHeader<'a> {
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

impl<'a> TranslationsHeader<'a> {
    const BLOB_MAGIC: &'static [u8] = b"TRTR00";
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
        let magic = reader.read(Self::BLOB_MAGIC.len())?;
        if magic != Self::BLOB_MAGIC {
            return Err(INVALID_TRANSLATIONS_BLOB);
        }

        // read length of contained data
        let container_length = reader.read_u16_le()? as usize;
        // continue working on the contained data (i.e., read beyond the bounds of
        // container_length will result in EOF).
        let mut reader = reader.read_stream(container_length.min(reader.remaining()))?;

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

        let data_len = header_reader.read_u16_le()? as usize;
        let data_hash: sha256::Digest =
            unwrap!(header_reader.read(sha256::DIGEST_SIZE)?.try_into());

        // ignore the rest of the header reader - this allows older firmware to
        // understand newer header if there are only added items
        _ = header_reader.rest();

        //
        // 3. parse the proof section
        //
        let mut proof_reader = read_u16_prefixed_block(&mut reader)?;
        let proof_count = proof_reader.read_byte()? as usize;
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
        if container_length - reader.tell() != data_len {
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
            total_len: container_length + Self::BLOB_MAGIC.len() + mem::size_of::<u16>(),
        };
        new.verify()?;
        Ok((new, reader))
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
        let mut result = self.verify_with_keys(&public_keys::PUBLIC_KEYS);
        #[cfg(feature = "debug")]
        if result.is_err() {
            // allow development keys
            result = self.verify_with_keys(&public_keys::PUBLIC_KEYS_DEVEL);
        }
        result
    }
}
