//! generated from webauthn_icons.rs.mako
//! (by running `make templates` in `core`)
//! do not edit manually!

use crate::ui::display::toif::NamedToif;


const ICON_AWS: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_aws.toif"), "AWS");
const ICON_BINANCE: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_binance.toif"), "BINANCE");
const ICON_BITBUCKET: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_bitbucket.toif"), "BITBUCKET");
const ICON_BITFINEX: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_bitfinex.toif"), "BITFINEX");
const ICON_BITWARDEN: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_bitwarden.toif"), "BITWARDEN");
const ICON_CLOUDFLARE: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_cloudflare.toif"), "CLOUDFLARE");
const ICON_COINBASE: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_coinbase.toif"), "COINBASE");
const ICON_DASHLANE: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_dashlane.toif"), "DASHLANE");
const ICON_DROPBOX: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_dropbox.toif"), "DROPBOX");
const ICON_DUO: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_duo.toif"), "DUO");
const ICON_FACEBOOK: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_facebook.toif"), "FACEBOOK");
const ICON_FASTMAIL: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_fastmail.toif"), "FASTMAIL");
const ICON_FEDORA: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_fedora.toif"), "FEDORA");
const ICON_GANDI: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_gandi.toif"), "GANDI");
const ICON_GEMINI: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_gemini.toif"), "GEMINI");
const ICON_GITHUB: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_github.toif"), "GITHUB");
const ICON_GITLAB: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_gitlab.toif"), "GITLAB");
const ICON_GOOGLE: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_google.toif"), "GOOGLE");
const ICON_INVITY: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_invity.toif"), "INVITY");
const ICON_KEEPER: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_keeper.toif"), "KEEPER");
const ICON_KRAKEN: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_kraken.toif"), "KRAKEN");
const ICON_LOGIN_GOV: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_login.gov.toif"), "LOGIN_GOV");
const ICON_MICROSOFT: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_microsoft.toif"), "MICROSOFT");
const ICON_MOJEID: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_mojeid.toif"), "MOJEID");
const ICON_NAMECHEAP: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_namecheap.toif"), "NAMECHEAP");
const ICON_PROTON: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_proton.toif"), "PROTON");
const ICON_SLUSHPOOL: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_slushpool.toif"), "SLUSHPOOL");
const ICON_STRIPE: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_stripe.toif"), "STRIPE");
const ICON_TUTANOTA: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_tutanota.toif"), "TUTANOTA");
/// Default icon when app does not have its own
const ICON_WEBAUTHN: NamedToif = NamedToif(include_res!("model_tt/res/fido/icon_webauthn.toif"), "WEBAUTHN");

/// Translates icon name into its data.
/// Returns default `ICON_WEBAUTHN` when the icon is not found or name not
/// supplied.
pub fn get_fido_icon_data<T: AsRef<str>>(icon_name: Option<T>) -> NamedToif {
    if let Some(icon_name) = icon_name {
        match icon_name.as_ref() {
            "aws" => ICON_AWS,
            "binance" => ICON_BINANCE,
            "bitbucket" => ICON_BITBUCKET,
            "bitfinex" => ICON_BITFINEX,
            "bitwarden" => ICON_BITWARDEN,
            "cloudflare" => ICON_CLOUDFLARE,
            "coinbase" => ICON_COINBASE,
            "dashlane" => ICON_DASHLANE,
            "dropbox" => ICON_DROPBOX,
            "duo" => ICON_DUO,
            "facebook" => ICON_FACEBOOK,
            "fastmail" => ICON_FASTMAIL,
            "fedora" => ICON_FEDORA,
            "gandi" => ICON_GANDI,
            "gemini" => ICON_GEMINI,
            "github" => ICON_GITHUB,
            "gitlab" => ICON_GITLAB,
            "google" => ICON_GOOGLE,
            "invity" => ICON_INVITY,
            "keeper" => ICON_KEEPER,
            "kraken" => ICON_KRAKEN,
            "login.gov" => ICON_LOGIN_GOV,
            "microsoft" => ICON_MICROSOFT,
            "mojeid" => ICON_MOJEID,
            "namecheap" => ICON_NAMECHEAP,
            "proton" => ICON_PROTON,
            "slushpool" => ICON_SLUSHPOOL,
            "stripe" => ICON_STRIPE,
            "tutanota" => ICON_TUTANOTA,
            _ => ICON_WEBAUTHN,
        }
    } else {
        ICON_WEBAUTHN
    }
}
