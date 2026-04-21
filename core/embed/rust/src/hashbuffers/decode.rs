use core::{convert::TryInto, str};

use bytemuck::AnyBitPattern;

use crate::{
    error::{value_error, Error},
    hashbuffers::codec::CodecError,
    micropython::{buffer, gc::Gc, list::List, obj::Obj, qstr::Qstr, util},
    protobuf::defs::EnumDef,
};

use crate::protobuf::{
    decode::Decoder as PbDecoder,
    defs::{FieldDef, FieldType, MsgDef},
    error,
    obj::MsgDefObj,
};

use super::codec::{
    table::{BlockOrLink, TableBlock},
    BlockData, DataBlock, SlotsBlock,
};

impl From<CodecError> for Error {
    fn from(e: CodecError) -> Self {
        dbg_println!("Hashbuffers codec error: {:?}", e);
        value_error!(c"Hashbuffers codec error")
    }
}

pub extern "C" fn hashbuffers_decode(buf: Obj, msg_def: Obj, enable_experimental: Obj) -> Obj {
    let block = || {
        let def = Gc::<MsgDefObj>::try_from(msg_def)?;
        let enable_experimental = bool::try_from(enable_experimental)?;

        if !enable_experimental && def.msg().is_experimental {
            return Err(error::experimental_not_enabled());
        }

        let buf = unsafe { buffer::get_buffer(buf) }?;

        HbDecoder::decode_data(buf, def.msg(), enable_experimental)
    };
    unsafe { util::try_or_raise(block) }
}

pub struct HbDecoder<'a> {
    pb_decoder: PbDecoder,
    table: TableBlock<'a>,
}

impl<'a> HbDecoder<'a> {
    pub fn new(table: TableBlock<'a>, enable_experimental: bool) -> Self {
        Self {
            pb_decoder: PbDecoder {
                enable_experimental,
            },
            table,
        }
    }

    /// Decode a TABLE block into a MicroPython message object.
    pub fn decode_data(
        data: &'a [u8],
        msg: &MsgDef,
        enable_experimental: bool,
    ) -> Result<Obj, Error> {
        let block_data = BlockData::new_from_prefix(data)?;
        let table = TableBlock::parse(block_data)?;
        let decoder = Self::new(table, enable_experimental);
        decoder.decode_by(msg)
    }

    pub fn decode_by(&self, msg: &MsgDef) -> Result<Obj, Error> {
        let mut obj = self.pb_decoder.empty_message(msg)?;
        // SAFETY: We assume that `obj` is not aliased here.
        let map = unsafe { Gc::as_mut(&mut obj) }.map_mut();

        for field in msg.fields {
            if field.is_experimental() && !self.pb_decoder.enable_experimental {
                continue;
            }

            let field_name = Qstr::from(field.name);

            if field.is_repeated() {
                let value = self.decode_repeated(field)?;
                map.set(field_name, value)?;
            } else {
                let value = self.decode_singular(field)?;
                map.set(field_name, value)?;
            }
        }

        self.pb_decoder.decode_defaults_into(msg, map)?;
        self.pb_decoder.assign_required_into(msg, map)?;
        Ok(obj.into())
    }

    /// Decode a singular (non-repeated) field from a vtable entry.
    fn decode_singular(&self, field: &FieldDef) -> Result<Obj, Error> {
        let vidx = field.tag as usize - 1;
        let name = Qstr::from(field.name);
        dbg_println!("Decoding singular field: ({}) {}", vidx, name.as_str());
        match field.get_type() {
            FieldType::UVarInt => Obj::try_from_option(self.table.get_u32(vidx)),
            FieldType::UVarInt64 => Obj::try_from_option(self.table.get_u64(vidx)),
            FieldType::SVarInt => Obj::try_from_option(self.table.get_i32(vidx)),
            FieldType::SVarInt64 => Obj::try_from_option(self.table.get_i64(vidx)),
            FieldType::Bool => self.decode_bool(field, vidx),
            FieldType::Enum(enum_type) => self.decode_enum(field, vidx, enum_type),
            FieldType::Bytes => self.decode_bytes(field, vidx),
            FieldType::String => self.decode_string(field, vidx),
            FieldType::Msg(msg_type) => self
                .get_block(vidx)?
                .map(|block| {
                    let table = TableBlock::parse(block)?;
                    let decoder = HbDecoder::new(table, self.pb_decoder.enable_experimental);
                    decoder.decode_by(&msg_type)
                })
                .unwrap_or(Ok(Obj::const_none())),
        }
    }

    fn decode_bool(&self, field: &FieldDef, vidx: usize) -> Result<Obj, Error> {
        let value = self.table.get_u8(vidx);
        match value {
            Some(0) => Ok(Obj::const_false()),
            Some(1) => Ok(Obj::const_true()),
            None => Ok(Obj::const_none()),
            _ => Err(error::invalid_value(field.name.into())),
        }
    }

    fn decode_enum(&self, field: &FieldDef, vidx: usize, enum_type: EnumDef) -> Result<Obj, Error> {
        let value = self.table.get_u16(vidx);
        let Some(value) = value else {
            return Ok(Obj::const_none());
        };
        enum_type
            .into_obj(value)
            .map_err(|_| error::invalid_value(field.name.into()))
    }

    fn get_block(&self, vidx: usize) -> Result<Option<BlockData<'a>>, Error> {
        let Some(block_or_link) = self.table.get_block_or_link(vidx)? else {
            return Ok(None);
        };
        let BlockOrLink::Block(block) = block_or_link else {
            dbg_println!("XXX Expected block, got link");
            return Ok(None);
        };
        Ok(Some(block))
    }

    fn get_datablock(&self, field: &FieldDef, vidx: usize) -> Result<Option<DataBlock<'a>>, Error> {
        self.get_block(vidx)?
            .map(|block| {
                DataBlock::parse(block).map_err(|_| error::invalid_value(field.name.into()))
            })
            .transpose()
    }

    fn decode_bytes(&self, field: &FieldDef, vidx: usize) -> Result<Obj, Error> {
        if let Some(data) = self.table.get_direct_data(vidx) {
            return data.try_into();
        }
        match self.get_datablock(field, vidx)? {
            Some(data_block) => {
                let data = data_block.as_slice::<u8>()?;
                data.try_into()
            }
            None => Ok(Obj::const_none()),
        }
    }

    fn decode_string(&self, field: &FieldDef, vidx: usize) -> Result<Obj, Error> {
        if let Some(data) = self.table.get_direct_data(vidx) {
            let unicode =
                str::from_utf8(data).map_err(|_| error::invalid_value(field.name.into()))?;
            return unicode.try_into();
        }
        match self.get_datablock(field, vidx)? {
            Some(block) => {
                let data = block.as_slice::<u8>()?;
                let unicode =
                    str::from_utf8(data).map_err(|_| error::invalid_value(field.name.into()))?;
                unicode.try_into()
            }
            None => Ok(Obj::const_none()),
        }
    }

    fn datablock_to_slice<T>(&self, field: &FieldDef, vidx: usize) -> Result<&'a [T], Error>
    where
        T: AnyBitPattern,
        T: TryInto<Obj>,
        <T as TryInto<Obj>>::Error: Into<Error>,
    {
        let data_block = self.get_datablock(field, vidx)?;
        let Some(data_block) = data_block else {
            return Ok(&[]);
        };
        Ok(data_block.as_slice::<T>()?)
    }

    fn repeated_to_list<T>(&self, field: &FieldDef, vidx: usize) -> Result<Gc<List>, Error>
    where
        T: AnyBitPattern,
        T: TryInto<Obj, Error = Error>,
    {
        let slice = self.datablock_to_slice::<T>(field, vidx)?;
        let list = List::from_iter(slice.iter().copied())?;
        Ok(list.leak())
    }

    /// Decode a repeated field from a vtable entry.
    fn decode_repeated(&self, field: &FieldDef) -> Result<Gc<List>, Error> {
        let vidx = field.tag as usize - 1;

        match field.get_type() {
            FieldType::UVarInt => self.repeated_to_list::<u32>(field, vidx),
            FieldType::UVarInt64 => self.repeated_to_list::<u64>(field, vidx),
            FieldType::SVarInt => self.repeated_to_list::<i32>(field, vidx),
            FieldType::SVarInt64 => self.repeated_to_list::<i64>(field, vidx),
            FieldType::Bool => {
                let slice = self.datablock_to_slice::<u8>(field, vidx)?;
                if slice.iter().any(|&value| value != 0 && value != 1) {
                    return Err(error::invalid_value(field.name.into()));
                }
                let list = List::from_iter(slice.iter().map(|&value| value != 0))?;
                Ok(list.leak())
            }
            FieldType::Enum(enum_type) => {
                let slice = self.datablock_to_slice::<u16>(field, vidx)?;
                // check errors in advance, we can't do that inside List::from_iter
                for elem in slice {
                    if !enum_type.values.contains(&elem) {
                        return Err(error::invalid_value(field.name.into()));
                    }
                }
                let list = List::from_iter(
                    slice
                        .iter()
                        .map(|&value| unwrap!(enum_type.into_obj(value))),
                )?;
                Ok(list.leak())
            }
            FieldType::Bytes => self.decode_slots(field, vidx, |data| data.try_into()),
            FieldType::String => self.decode_slots(field, vidx, |data| {
                let unicode =
                    str::from_utf8(data).map_err(|_| error::invalid_value(field.name.into()))?;
                unicode.try_into()
            }),
            FieldType::Msg(msg_type) => self.decode_msg_table(field, vidx, msg_type),
        }
    }

    fn decode_slots(
        &self,
        field: &FieldDef,
        vidx: usize,
        map_fn: impl Fn(&[u8]) -> Result<Obj, Error>,
    ) -> Result<Gc<List>, Error> {
        let block_or_link = self.table.get_block_or_link(vidx)?;
        let Some(block_or_link) = block_or_link else {
            return Ok(List::alloc(&[])?.into());
        };
        let BlockOrLink::Block(block) = block_or_link else {
            return Ok(List::alloc(&[])?.into());
        };
        let slots_block =
            SlotsBlock::parse(block).map_err(|_| error::invalid_value(field.name.into()))?;
        let mut list = List::with_capacity(slots_block.len())?;
        for elem in slots_block.iter_elements() {
            list.append(map_fn(elem)?)?;
        }
        Ok(list.leak())
    }

    fn decode_msg_table(
        &self,
        field: &FieldDef,
        vidx: usize,
        msg_type: MsgDef,
    ) -> Result<Gc<List>, Error> {
        let block_or_link = self.table.get_block_or_link(vidx)?;
        let Some(block_or_link) = block_or_link else {
            return Ok(List::alloc(&[])?.into());
        };
        let BlockOrLink::Block(block) = block_or_link else {
            return Ok(List::alloc(&[])?.into());
        };
        let array =
            TableBlock::parse(block).map_err(|_| error::invalid_value(field.name.into()))?;
        let mut list = List::with_capacity(array.len())?;
        for i in 0..array.len() {
            let block_or_link = array.get_block_or_link(i)?;
            let Some(block_or_link) = block_or_link else {
                return Err(error::invalid_value(field.name.into()));
            };
            let BlockOrLink::Block(block) = block_or_link else {
                dbg_println!("XXX Expected block, got link");
                continue;
            };
            let table = TableBlock::parse(block)?;
            let decoder = HbDecoder::new(table, self.pb_decoder.enable_experimental);
            list.append(decoder.decode_by(&msg_type)?)?;
        }
        Ok(list.leak())
    }
}
