//! Flattened view of the messages and enums in a set of protobuf file
//! descriptors, in the shape the Python renderer needs.

use anyhow::{Result, bail};
use prost_types::{
    DescriptorProto, EnumDescriptorProto, FieldDescriptorProto, FileDescriptorSet,
    field_descriptor_proto::{Label, Type},
};

pub struct Definitions {
    pub enums: Vec<Enum>,
    pub messages: Vec<Message>,
}

pub struct Enum {
    pub name: String,
    pub values: Vec<(String, i32)>,
}

pub struct Message {
    pub name: String,
    pub fields: Vec<Field>,
}

pub struct Field {
    pub name: String,
    pub number: i32,
    /// Type name as used by `trezorlib.protobuf`: a scalar proto type name
    /// or the (unqualified) name of a message/enum.
    pub type_name: String,
    pub python_type: String,
    pub default_repr: String,
    pub required: bool,
    pub repeated: bool,
}

impl Field {
    pub fn optional(&self) -> bool {
        !self.required && !self.repeated
    }
}

impl Definitions {
    /// Collects messages and enums of all files in order: per file the
    /// top-level items first, then nested ones. Deprecated items are skipped.
    pub fn from_descriptors(set: &FileDescriptorSet) -> Result<Self> {
        let mut defs = Definitions {
            enums: Vec::new(),
            messages: Vec::new(),
        };

        for file in &set.file {
            let messages: Vec<_> = file
                .message_type
                .iter()
                .filter(|m| !is_message_deprecated(m))
                .collect();
            for message in &messages {
                defs.messages.push(Message::from_proto(message)?);
            }
            defs.add_enums(&file.enum_type);
            for message in messages {
                defs.add_nested(message)?;
            }
        }

        if defs.messages.is_empty() && defs.enums.is_empty() {
            bail!("No messages and no enums found.");
        }
        Ok(defs)
    }

    fn add_enums(&mut self, enums: &[EnumDescriptorProto]) {
        for e in enums {
            if !e.options.as_ref().is_some_and(|o| o.deprecated()) {
                self.enums.push(Enum::from_proto(e));
            }
        }
    }

    fn add_nested(&mut self, message: &DescriptorProto) -> Result<()> {
        let nested: Vec<_> = message
            .nested_type
            .iter()
            .filter(|m| !is_message_deprecated(m))
            .collect();
        for m in &nested {
            self.messages.push(Message::from_proto(m)?);
        }
        self.add_enums(&message.enum_type);
        for m in nested {
            self.add_nested(m)?;
        }
        Ok(())
    }
}

fn is_message_deprecated(message: &DescriptorProto) -> bool {
    message.options.as_ref().is_some_and(|o| o.deprecated())
}

impl Enum {
    fn from_proto(e: &EnumDescriptorProto) -> Self {
        let name = e.name().to_string();
        let values = e
            .value
            .iter()
            // Deprecated values are kept, as in the former `pb2py`.
            .map(|v| (strip_enum_prefix(&name, v.name()).to_string(), v.number()))
            .collect();
        Enum { name, values }
    }
}

impl Message {
    fn from_proto(m: &DescriptorProto) -> Result<Self> {
        let fields = m
            .field
            .iter()
            .filter(|f| !f.options.as_ref().is_some_and(|o| o.deprecated()))
            .map(Field::from_proto)
            .collect::<Result<_>>()?;
        Ok(Message {
            name: m.name().to_string(),
            fields,
        })
    }
}

impl Field {
    fn from_proto(f: &FieldDescriptorProto) -> Result<Self> {
        let ty = f.r#type();
        let type_name = if f.type_name().is_empty() {
            scalar_type_name(ty)?.to_string()
        } else {
            f.type_name()
                .rsplit('.')
                .next()
                .unwrap_or_default()
                .to_string()
        };
        let python_type = python_scalar_type(ty).map_or_else(|| type_name.clone(), str::to_string);

        let default_repr = match f.default_value {
            None => "None".to_string(),
            Some(ref value) => match ty {
                Type::Enum => format!("{type_name}.{}", strip_enum_prefix(&type_name, value)),
                Type::String => python_str_repr(value),
                Type::Bytes => format!("b{}", python_str_repr(value)),
                Type::Bool => if value == "true" { "True" } else { "False" }.to_string(),
                _ => value.clone(),
            },
        };

        Ok(Field {
            name: f.name().to_string(),
            number: f.number(),
            type_name,
            python_type,
            default_repr,
            required: f.label() == Label::Required,
            repeated: f.label() == Label::Repeated,
        })
    }
}

/// Generates the stripped-down enum value name, given the enum type name.
///
/// Handles new-style enums (`First_Value`), old-style enums prefixed with the
/// enum name (`SomeEnum_First_Value`) and old-style enums whose name ends in
/// `Type` while values are prefixed without it (`SomeEnumType` /
/// `SomeEnum_First_Value`).
pub(super) fn strip_enum_prefix<'a>(enum_name: &str, value_name: &'a str) -> &'a str {
    if let Some(rest) = value_name
        .strip_prefix(enum_name)
        .and_then(|r| r.strip_prefix('_'))
    {
        return rest;
    }
    if let Some(base) = enum_name.strip_suffix("Type")
        && let Some(rest) = value_name
            .strip_prefix(base)
            .and_then(|r| r.strip_prefix('_'))
    {
        return rest;
    }
    value_name
}

fn scalar_type_name(ty: Type) -> Result<&'static str> {
    Ok(match ty {
        Type::Double => "double",
        Type::Float => "float",
        Type::Int64 => "int64",
        Type::Uint64 => "uint64",
        Type::Int32 => "int32",
        Type::Fixed64 => "fixed64",
        Type::Fixed32 => "fixed32",
        Type::Bool => "bool",
        Type::String => "string",
        Type::Bytes => "bytes",
        Type::Uint32 => "uint32",
        Type::Sfixed32 => "sfixed32",
        Type::Sfixed64 => "sfixed64",
        Type::Sint32 => "sint32",
        Type::Sint64 => "sint64",
        Type::Group | Type::Message | Type::Enum => bail!("{ty:?} field without a type name"),
    })
}

fn python_scalar_type(ty: Type) -> Option<&'static str> {
    match ty {
        Type::Int64
        | Type::Uint64
        | Type::Int32
        | Type::Fixed64
        | Type::Fixed32
        | Type::Uint32
        | Type::Sfixed32
        | Type::Sfixed64
        | Type::Sint32
        | Type::Sint64 => Some("int"),
        Type::Double | Type::Float => Some("float"),
        Type::Bool => Some("bool"),
        Type::String => Some("str"),
        Type::Bytes => Some("bytes"),
        Type::Group | Type::Message | Type::Enum => None,
    }
}

/// Python-style `repr()` of a string, using single quotes unless the string
/// contains a single quote and no double quote.
fn python_str_repr(s: &str) -> String {
    let quote = if s.contains('\'') && !s.contains('"') {
        '"'
    } else {
        '\''
    };
    let mut out = String::new();
    out.push(quote);
    for c in s.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c == quote => {
                out.push('\\');
                out.push(c);
            }
            c => out.push(c),
        }
    }
    out.push(quote);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strip_prefix_new_style() {
        assert_eq!(strip_enum_prefix("SomeEnum", "First_Value"), "First_Value");
    }

    #[test]
    fn strip_prefix_old_style() {
        assert_eq!(
            strip_enum_prefix("SomeEnum", "SomeEnum_First_Value"),
            "First_Value"
        );
    }

    #[test]
    fn strip_prefix_old_style_with_type() {
        assert_eq!(strip_enum_prefix("SomeEnumType", "SomeEnum_First"), "First");
        assert_eq!(
            strip_enum_prefix("MessageType", "MessageType_GetAddress"),
            "GetAddress"
        );
    }

    #[test]
    fn strip_prefix_requires_underscore_separator() {
        assert_eq!(strip_enum_prefix("Some", "SomeValue"), "SomeValue");
    }

    #[test]
    fn str_repr() {
        assert_eq!(python_str_repr(""), "''");
        assert_eq!(python_str_repr("it's"), "\"it's\"");
        assert_eq!(python_str_repr("a\\b\n"), "'a\\\\b\\n'");
    }
}
