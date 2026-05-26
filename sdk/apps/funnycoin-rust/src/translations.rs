// Include generated translations

include!(concat!(env!("OUT_DIR"), "/translations.rs"));

#[cfg(test)]
mod tests {

    #[test]
    #[cfg(feature = "lang_en")]
    fn test_lang_eng() {
        assert!(cfg!(feature = "lang_en"));
        assert!(!cfg!(feature = "lang_cs"));
    }

    #[test]
    #[cfg(feature = "lang_cs")]
    fn test_lang_cs() {
        assert!(cfg!(feature = "lang_cs"));
        assert!(!cfg!(feature = "lang_en"));
    }
    #[test]
    fn test_known_keys_compile() {
        // If a key is missing in the current lang's JSON this won't compile
        let _ = tr!("words__title_done");
        let _ = tr!("instructions__continue_in_app");
        let _ = tr!("address__public_key");
        let _ = tr!("address__public_key_confirmed");
    }

    #[test]
    #[cfg(feature = "lang_en")]
    fn test_english_values() {
        assert_eq!(tr!("words__title_done"), "Done");
        assert_eq!(tr!("instructions__continue_in_app"), "Continue in the app");
        assert_eq!(tr!("address__public_key"), "Public key");
        assert_eq!(tr!("address__public_key_confirmed"), "Public key confirmed");
    }

    #[test]
    #[cfg(feature = "lang_cs")]
    fn test_czech_values() {
        assert_eq!(tr!("words__title_done"), "Hotovo");
        assert_eq!(
            tr!("instructions__continue_in_app"),
            "Pokračujte v aplikaci"
        );
        assert_eq!(tr!("address__public_key"), "Veřejný klíč");
        assert_eq!(
            tr!("address__public_key_confirmed"),
            "Veřejný klíč potvrzen"
        );
    }
}
