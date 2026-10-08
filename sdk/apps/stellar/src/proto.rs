// Include generated protobuf code
//
// The generated `stellar` messages refer to `super::super::common`, so the
// modules mirror the protobuf package nesting (`hw.trezor.messages.stellar`
// next to `hw.trezor.common`) and are re-exported flat below.

mod hw_trezor {
    pub mod common {
        include!(concat!(env!("OUT_DIR"), "/hw.trezor.common.rs"));
    }

    pub mod messages {
        include!(concat!(env!("OUT_DIR"), "/hw.trezor.messages.rs"));

        pub mod stellar {
            include!(concat!(env!("OUT_DIR"), "/hw.trezor.messages.stellar.rs"));
        }
    }
}

pub use hw_trezor::{common, messages, messages::stellar};

#[cfg(test)]
mod tests {
    use super::messages::MessageType;

    #[test]
    fn message_type_max_discriminant() {
        // Find the largest valid discriminant for MessageType
        let mut max_value = i32::MIN;
        for i in 0..=1000 {
            if MessageType::try_from(i).is_ok() {
                max_value = i;
            }
        }
        // Message IDs travel as u16 on the wire
        assert!(
            max_value <= u16::MAX as i32,
            "MessageType max value {} does not fit in u16",
            max_value
        );
    }
}
