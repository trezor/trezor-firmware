
- automatizace nastaveni sau a mpu (pouziti symbolu z linker skriptu)
- navrhnout hlavicku neprivilegovane aplikace
- navrh secure API, core API
// - dalsi zkoumani trustzone na STM32U5 (rozdeleni zodpovednosti mezi secure a privileged)


//- prozkoumat primy prechod z unsecure+unprivileged do secure+privileged
//- core_api, kopirovani a kontrola parametru, ochrana proti TOCTOU utoku
//- secure_api, kopirovani a kontrola parametru, cmse_check_address_range() (TT instrukce)
//- dalsich zkoumani Cortex-M33 (registry cpu)
//- nastudovovat zranitelnosti https://cactilab.github.io/assets/pdf/ret2ns2023.pdf
//- prechod secure -> unsecure, vynulovat registry


