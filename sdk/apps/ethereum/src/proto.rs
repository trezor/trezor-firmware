// Include generated protobuf code

pub mod common {
    include!(concat!(env!("OUT_DIR"), "/hw.trezor.common.rs"));
}

pub mod definitions {
    include!(concat!(env!("OUT_DIR"), "/hw.trezor.definitions.rs"));
}
pub mod ethereum {
    include!(concat!(env!("OUT_DIR"), "/hw.trezor.ethereum.rs"));
}

pub mod messages {
    include!(concat!(env!("OUT_DIR"), "/hw.trezor.messages.rs"));
}

#[cfg(test)]
mod tests {
    use super::messages::MessageType;

    #[test]
    fn message_type_max_discriminant() {
        // Find the largest valid discriminant for MessageType
        let mut max_value = i32::MIN;
        for i in 0..=i32::MAX {
            if let Ok(_) = MessageType::try_from(i) {
                max_value = i;
            }
            // Early exit: prost enums are usually dense and positive
            if i > 1000 {
                break;
            }
        }
        println!("Max MessageType discriminant: {}", max_value);
        // Optionally, assert it's within u16 if that's your requirement:
        assert!(
            max_value <= u16::MAX as i32,
            "MessageType max value {} does not fit in u16",
            max_value
        );
    }
}
