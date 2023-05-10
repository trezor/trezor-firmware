mod button;
mod button_controller;
mod common;
mod error;
mod hold_to_confirm;
mod input_methods;
mod loader;
mod result;
mod welcome_screen;

use super::theme;
pub use button::{
    Button, ButtonAction, ButtonActions, ButtonContent, ButtonDetails, ButtonLayout, ButtonMsg,
    ButtonPos, ButtonStyle, ButtonStyleSheet,
};
pub use button_controller::{ButtonController, ButtonControllerMsg};
pub use error::ErrorScreen;
pub use hold_to_confirm::{HoldToConfirm, HoldToConfirmMsg};
pub use input_methods::{
    choice::{Choice, ChoiceFactory, ChoicePage, ChoicePageMsg},
    choice_item::ChoiceItem,
};
pub use loader::{Loader, LoaderMsg, LoaderStyle, LoaderStyleSheet};
pub use result::ResultScreen;
pub use welcome_screen::WelcomeScreen;

#[cfg(feature = "micropython")]
mod address_details;
#[cfg(feature = "micropython")]
mod changing_text;
#[cfg(feature = "micropython")]
mod coinjoin_progress;
#[cfg(feature = "micropython")]
mod flow;
#[cfg(feature = "micropython")]
mod flow_pages;
#[cfg(feature = "micropython")]
mod flow_pages_helpers;
#[cfg(feature = "micropython")]
mod frame;
#[cfg(feature = "micropython")]
mod homescreen;
#[cfg(feature = "micropython")]
mod no_btn_dialog;
#[cfg(feature = "micropython")]
mod page;
#[cfg(feature = "micropython")]
mod progress;
#[cfg(feature = "micropython")]
mod result_anim;
#[cfg(feature = "micropython")]
mod result_popup;
#[cfg(feature = "micropython")]
mod scrollbar;
#[cfg(feature = "micropython")]
mod share_words;
#[cfg(feature = "micropython")]
mod show_more;
#[cfg(feature = "micropython")]
mod title;

#[cfg(feature = "micropython")]
pub use address_details::{AddressDetails, AddressDetailsMsg};

#[cfg(feature = "micropython")]
pub use changing_text::ChangingTextLine;
#[cfg(feature = "micropython")]
pub use coinjoin_progress::CoinJoinProgress;
#[cfg(feature = "micropython")]
pub use flow::{Flow, FlowMsg};
#[cfg(feature = "micropython")]
pub use flow_pages::{FlowPages, Page};
#[cfg(feature = "micropython")]
pub use frame::{Frame, ScrollableContent, ScrollableFrame};
#[cfg(feature = "micropython")]
pub use homescreen::{Homescreen, HomescreenMsg, Lockscreen};
#[cfg(feature = "micropython")]
pub use input_methods::{
    number_input::{NumberInput, NumberInputMsg},
    passphrase::{PassphraseEntry, PassphraseEntryMsg},
    pin::{PinEntry, PinEntryMsg},
    simple_choice::{SimpleChoice, SimpleChoiceMsg},
    wordlist::{WordlistEntry, WordlistEntryMsg, WordlistType},
};
#[cfg(feature = "micropython")]
pub use no_btn_dialog::{NoBtnDialog, NoBtnDialogMsg};
#[cfg(feature = "micropython")]
pub use page::ButtonPage;
#[cfg(feature = "micropython")]
pub use progress::Progress;
#[cfg(feature = "micropython")]
pub use result_anim::{ResultAnim, ResultAnimMsg};
#[cfg(feature = "micropython")]
pub use result_popup::{ResultPopup, ResultPopupMsg};
#[cfg(feature = "micropython")]
pub use scrollbar::ScrollBar;
#[cfg(feature = "micropython")]
pub use share_words::ShareWords;
#[cfg(feature = "micropython")]
pub use show_more::{CancelInfoConfirmMsg, ShowMore};
