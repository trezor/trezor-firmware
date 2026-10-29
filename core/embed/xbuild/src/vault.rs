//! Compile-time record algorithm and key backend selection.

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Cipher {
    Gcm = 3,
}
impl Cipher {
    fn parse(value: &str) -> Result<Self, String> {
        match value {
            "gcm" => Ok(Self::Gcm),
            _ => Err(format!(
                "This feature branch supports only gcm records: {value}"
            )),
        }
    }
    pub fn define(self) -> &'static str {
        "3"
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct Capabilities {
    pub saes: bool,
    pub native_gcm: bool,
}
impl Capabilities {
    pub fn for_mcu(mcu: &str) -> Self {
        match mcu {
            "stm32u58" | "stm32u5a" | "stm32u5g" => Self {
                saes: true,
                native_gcm: false,
            },
            // Capability description, not an H5 board/HAL implementation.
            "stm32h5f4" => Self {
                saes: true,
                native_gcm: true,
            },
            _ => Self::default(),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Selection {
    pub cipher: Cipher,
    pub hardware: bool,
    pub native_gcm: bool,
    pub legacy_fallback: bool,
}
impl Selection {
    pub fn resolve(
        mode: Option<&str>,
        cipher: Option<&str>,
        backend: Option<&str>,
        caps: Capabilities,
    ) -> Result<Self, String> {
        if mode.is_some() && (cipher.is_some() || backend.is_some()) {
            return Err("Use TREZOR_VAULT_MODE or TREZOR_VAULT_CIPHER/BACKEND, not both".into());
        }
        let (cipher, hardware, legacy_fallback) = if let Some(mode) = mode {
            let (name, requested) = if mode == "saes" {
                ("gcm", true)
            } else if let Some(name) = mode.strip_prefix("saes-") {
                (name, true)
            } else {
                (mode, false)
            };
            (
                Cipher::parse(name)?,
                requested && caps.saes,
                requested && !caps.saes,
            )
        } else {
            let hardware = match backend.unwrap_or("auto") {
                "auto" => caps.saes,
                "software" => false,
                "saes" if caps.saes => true,
                "saes" => return Err("SAES backend requested on an MCU without SAES".into()),
                value => return Err(format!("Unsupported vault backend: {value}")),
            };
            (Cipher::parse(cipher.unwrap_or("gcm"))?, hardware, false)
        };
        Ok(Self {
            cipher,
            hardware,
            native_gcm: hardware && caps.native_gcm,
            legacy_fallback,
        })
    }

    /// Production keeps record keys in SAES wherever the MCU has it: the
    /// software backend unwraps the record key and expands its schedule in
    /// RAM for every operation.
    pub fn check_production(&self, caps: Capabilities) -> Result<(), String> {
        if caps.saes && !self.hardware {
            return Err(
                "Software vault sealing is not allowed in production on an MCU with SAES".into(),
            );
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn feature_rejects_other_record_algorithms() {
        for name in ["gcm", "siv", "kwp", "ecb"] {
            assert_eq!(
                Selection::resolve(None, Some(name), Some("software"), Capabilities::default())
                    .is_ok(),
                name == "gcm"
            );
        }
    }
    #[test]
    fn backend_and_native_capabilities_preserve_the_record_format() {
        for mcu in ["stm32f427", "stm32u58", "stm32h5f4"] {
            let caps = Capabilities::for_mcu(mcu);
            let soft = Selection::resolve(None, None, Some("software"), caps).unwrap();
            assert!(!soft.hardware);
            let hw = Selection::resolve(None, None, Some("saes"), caps);
            assert_eq!(hw.is_ok(), caps.saes);
            if let Ok(hw) = hw {
                assert_eq!(hw.cipher, soft.cipher);
                assert_eq!(hw.native_gcm, caps.native_gcm);
                assert!(hw.check_production(caps).is_ok());
                assert!(soft.check_production(caps).is_err());
            }
        }
    }
    #[test]
    fn mixed_configuration_is_rejected() {
        assert!(
            Selection::resolve(Some("gcm"), Some("gcm"), None, Capabilities::default()).is_err()
        );
        assert!(Selection::resolve(None, None, Some("saes"), Capabilities::default()).is_err());
    }
}
