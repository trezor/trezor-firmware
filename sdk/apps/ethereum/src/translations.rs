// Include generated translations

include!(concat!(env!("OUT_DIR"), "/translations.rs"));

#[cfg(test)]
mod tests {
    #[test]
    fn test_known_key_compile() {
        // If a key is missing in the current lang's JSON this won't compile
        let _ = tr!("words__title_done");
    }

    #[test]
    #[cfg(feature = "lang_en")]
    fn test_english_key() {
        assert_eq!(tr!("words__title_done"), "Done");
    }

    #[test]
    #[cfg(feature = "lang_cs")]
    fn test_czech_key() {
        assert_eq!(tr!("words__title_done"), "Hotovo");
    }

    #[test]
    #[cfg(all(feature = "lang_en", feature = "model_t3w1"))]

    fn test_english_eckhart_key() {
        assert_eq!(
            tr!("ethereum__title_token_contract"),
            "Token contract address"
        );
    }

    #[cfg(all(feature = "lang_en", feature = "model_t3t1"))]

    fn test_english_delizia_key() {
        assert_eq!(tr!("ethereum__title_token_contract"), "Token contract");
    }
}
