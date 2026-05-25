use hashbuffers::{table::BlockOrLink, BlockData, BlockType, DataBlock, Link, TableBlock};
use micropython::{
    buffer::get_buffer,
    gc::{Gc, GcBox},
    qstr::Attribute,
    Obj,
};

use crate::protobuf::defs::{FieldDef, FieldType, MsgDef};

use super::error::{self, Error};

struct SharedBlock(Gc<[u8]>);

impl SharedBlock {
    pub fn from_slice(data: &[u8]) -> Result<Self, Error> {
        Ok(Self(GcBox::from_slice(data)?.leak()))
    }
}

impl AsRef<[u8]> for SharedBlock {
    fn as_ref(&self) -> &[u8] {
        self.0.as_ref()
    }
}

pub struct LoadedBlock {
    data: GcBox<[u8]>,
    block_offset: usize,
}

impl LoadedBlock {
    pub fn new(data: GcBox<[u8]>, block_offset: usize) -> Result<Self, Error> {
        todo!()
    }

    pub fn block_data<'a>(&'a self) -> BlockData<'a> {
        // should never fail, we construct a LoadedBlock from a pre-validated block
        BlockData::new_from_prefix(&self.data[self.block_offset..]).unwrap()
    }
}

pub enum LazyBlock {
    Loaded(LoadedBlock),
    Link(Link),
}

impl LazyBlock {
    pub fn is_loaded(&self) -> bool {
        matches!(self, LazyBlock::Loaded(_))
    }

    pub fn load(&mut self, buffer: GcBox<[u8]>) -> Result<(), Error> {
        *self = LazyBlock::Loaded(LoadedBlock::new(buffer, 0));
        Ok(())
    }
}

pub struct HbLazyTable {
    buffer: Option<GcBox<[u8]>>,
    def: &'static MsgDef,
    block_offset: usize,
}

impl HbLazyTable {
    pub fn new(buffer_obj: Obj, def: &'static MsgDef) -> Result<Self, Error> {
        let buffer = {
            // SAFETY: we make a copy and then dispose of the reference
            let tmp_buffer_ref = unsafe { get_buffer(buffer_obj) }?;
            GcBox::from_slice(tmp_buffer_ref)
        }?;

        let block_data = BlockData::new_from_prefix(buffer.as_ref())?;
        let table = TableBlock::parse(block_data)?;
        Self::validate(def, &table)?;

        Ok(Self {
            buffer,
            def,
            table_offset: 0,
        })
    }

    pub fn validate(def: &MsgDef, table: &TableBlock) -> Result<(), Error> {
        for field in def.fields {
            Self::validate_field(field, table)?;
        }
        Ok(())
    }

    fn validate_field(field: &FieldDef, table: &TableBlock) -> Result<(), Error> {
        if field.is_repeated() {
            Self::validate_repeated_field(field, table)
        } else {
            Self::validate_singular_field(field, table)
        }
    }

    fn validate_array_of<'a, T: bytemuck::AnyBitPattern>(
        table: &'a TableBlock,
        idx: usize,
        field_name: Attribute,
    ) -> Result<&'a [T], Error> {
        match table.get_block_or_link(idx)? {
            None => Ok(&[]),
            Some(BlockOrLink::Link(_)) => Ok(&[]),
            Some(BlockOrLink::Block(block)) => {
                let data = DataBlock::parse(block)?;
                data.as_slice::<T>()
                    .map_err(|_| error::invalid_encoding(field_name).into())
            }
        }
    }

    fn validate_singular_field(field: &FieldDef, table: &TableBlock) -> Result<(), Error> {
        if field.is_required() && table.get_entry(field.tag as usize - 1).is_null() {
            return Err(error::missing_required_field(field.name()).into());
        }

        let idx = field.tag as usize - 1;
        match field.get_type() {
            FieldType::UVarInt => {
                table.try_get_u32(idx)?;
            }
            FieldType::UVarInt64 => {
                table.try_get_u64(idx)?;
            }
            FieldType::SVarInt => {
                table.try_get_i32(idx)?;
            }
            FieldType::SVarInt64 => {
                table.try_get_i64(idx)?;
            }
            FieldType::Bool => {
                let value = table.try_get_u8(idx)?;
                match value {
                    Some(0) | Some(1) | None => (),
                    _ => return Err(error::invalid_encoding(field.name()).into()),
                }
            }
            FieldType::Enum(enum_def) => {
                let value = table.try_get_u16(idx)?;
                match value {
                    Some(v) if enum_def.values.contains(&v) => (),
                    _ => return Err(error::invalid_encoding(field.name()).into()),
                }
            }
            FieldType::Bytes => {
                Self::validate_array_of::<u8>(table, idx, field.name())?;
            }
            FieldType::String => {
                let bytes = Self::validate_array_of::<u8>(table, idx, field.name())?;
                if core::str::from_utf8(bytes).is_err() {
                    return Err(error::invalid_value(field.name()).into());
                }
            }
            FieldType::Msg(msg_def) => match table.get_block_or_link(idx)? {
                // None is covered at start of function
                None => (),
                // not descending into links here
                Some(BlockOrLink::Link(_)) => (),
                Some(BlockOrLink::Block(block)) => {
                    let table = TableBlock::parse(block)?;
                    Self::validate(&msg_def, &table)?;
                }
            },
        };
        Ok(())
    }

    fn validate_repeated_field(field: &FieldDef, table: &TableBlock) -> Result<(), Error> {
        let idx = field.tag as usize - 1;
        match field.get_type() {
            FieldType::UVarInt | FieldType::SVarInt => {
                Self::validate_array_of::<u32>(table, idx, field.name())?;
            }
            FieldType::UVarInt64 | FieldType::SVarInt64 => {
                Self::validate_array_of::<u64>(table, idx, field.name())?;
            }
            FieldType::Bool => {
                let array = Self::validate_array_of::<u8>(table, idx, field.name())?;
                if array.iter().any(|&b| b != 0 && b != 1) {
                    return Err(error::invalid_value(field.name()).into());
                }
            }
            FieldType::Enum(enum_def) => {
                let array = Self::validate_array_of::<u16>(table, idx, field.name())?;
                if array.iter().any(|&v| !enum_def.values.contains(&v)) {
                    return Err(error::invalid_value(field.name()).into());
                }
            }
            FieldType::Bytes => todo!(),
            FieldType::String => todo!(),
            FieldType::Msg(msg_def) => todo!(),
        }
        Ok(())
    }
}
