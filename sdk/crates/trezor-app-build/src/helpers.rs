use std::env;

#[derive(Default)]
pub enum Language {
    #[default]
    English,
    Czech,
}

impl Language {
    pub fn from_env() -> Self {
        if env::var("CARGO_FEATURE_LANG_EN").is_ok() {
            Self::English
        } else if env::var("CARGO_FEATURE_LANG_CS").is_ok() {
            Self::Czech
        } else {
            Self::default()
        }
    }

    pub fn file(&self) -> String {
        let name = match self {
            Self::English => "en",
            Self::Czech => "cs",
        };
        format!("translations/{}.json", name)
    }
}

#[derive(Default)]
pub enum Model {
    #[default]
    T3W1,
    T3T1,
}

impl Model {
    pub fn from_env() -> Self {
        if env::var("CARGO_FEATURE_MODEL_T3W1").is_ok() {
            Self::T3W1
        } else if env::var("CARGO_FEATURE_MODEL_T3T1").is_ok() {
            Self::T3T1
        } else {
            Self::default()
        }
    }

    pub fn layout(&self) -> &'static str {
        match self {
            Self::T3W1 => "Eckhart",
            Self::T3T1 => "Delizia",
        }
    }
}

fn target_os_is(os: &str) -> bool {
    env::var("CARGO_CFG_TARGET_OS").is_ok_and(|v| v == os)
}

pub fn is_linux() -> bool {
    target_os_is("linux")
}

pub fn is_macos() -> bool {
    target_os_is("macos")
}

pub fn is_unit_test() -> bool {
    env::var("CARGO_FEATURE_TEST").is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Mutex, MutexGuard};

    const VARS: [&str; 6] = [
        "CARGO_FEATURE_LANG_EN",
        "CARGO_FEATURE_LANG_CS",
        "CARGO_FEATURE_MODEL_T3W1",
        "CARGO_FEATURE_MODEL_T3T1",
        "CARGO_FEATURE_TEST",
        "CARGO_CFG_TARGET_OS",
    ];

    /// Serializes tests that touch the process environment and clears the
    /// variables under test on both entry and exit.
    struct Env(#[allow(dead_code)] MutexGuard<'static, ()>);

    impl Env {
        fn new() -> Self {
            static LOCK: Mutex<()> = Mutex::new(());
            let guard = LOCK.lock().unwrap_or_else(|e| e.into_inner());
            Self::clear();
            Self(guard)
        }

        fn set(&self, vars: &[(&str, &str)]) {
            for (k, v) in vars {
                unsafe { env::set_var(k, v) };
            }
        }

        fn clear() {
            for k in VARS {
                unsafe { env::remove_var(k) };
            }
        }
    }

    impl Drop for Env {
        fn drop(&mut self) {
            Self::clear();
        }
    }

    #[test]
    fn language_defaults_to_english() {
        let _env = Env::new();
        assert_eq!(Language::from_env().file(), "translations/en.json");
    }

    #[test]
    fn language_from_feature() {
        let env = Env::new();
        env.set(&[("CARGO_FEATURE_LANG_CS", "1")]);
        assert_eq!(Language::from_env().file(), "translations/cs.json");
        Env::clear();
        env.set(&[("CARGO_FEATURE_LANG_EN", "1")]);
        assert_eq!(Language::from_env().file(), "translations/en.json");
    }

    #[test]
    fn language_prefers_english_when_both_set() {
        let env = Env::new();
        env.set(&[
            ("CARGO_FEATURE_LANG_EN", "1"),
            ("CARGO_FEATURE_LANG_CS", "1"),
        ]);
        assert_eq!(Language::from_env().file(), "translations/en.json");
    }

    #[test]
    fn model_defaults_to_t3w1() {
        let _env = Env::new();
        assert_eq!(Model::from_env().layout(), "Eckhart");
    }

    #[test]
    fn model_from_feature() {
        let env = Env::new();
        env.set(&[("CARGO_FEATURE_MODEL_T3T1", "1")]);
        assert_eq!(Model::from_env().layout(), "Delizia");
        Env::clear();
        env.set(&[("CARGO_FEATURE_MODEL_T3W1", "1")]);
        assert_eq!(Model::from_env().layout(), "Eckhart");
    }

    #[test]
    fn model_prefers_t3w1_when_both_set() {
        let env = Env::new();
        env.set(&[
            ("CARGO_FEATURE_MODEL_T3W1", "1"),
            ("CARGO_FEATURE_MODEL_T3T1", "1"),
        ]);
        assert_eq!(Model::from_env().layout(), "Eckhart");
    }

    #[test]
    fn target_os_detection() {
        let env = Env::new();
        assert!(!is_linux());
        assert!(!is_macos());

        env.set(&[("CARGO_CFG_TARGET_OS", "linux")]);
        assert!(is_linux());
        assert!(!is_macos());

        env.set(&[("CARGO_CFG_TARGET_OS", "macos")]);
        assert!(!is_linux());
        assert!(is_macos());

        env.set(&[("CARGO_CFG_TARGET_OS", "none")]);
        assert!(!is_linux());
        assert!(!is_macos());
    }

    #[test]
    fn unit_test_feature() {
        let env = Env::new();
        assert!(!is_unit_test());
        env.set(&[("CARGO_FEATURE_TEST", "1")]);
        assert!(is_unit_test());
    }
}
