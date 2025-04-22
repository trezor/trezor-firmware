pub mod bl_confirm;
mod button;
mod button_controller;
mod error;
mod hold_to_confirm;
mod input_methods;
mod loader;
mod result;
mod welcome_screen;

use super::{common_messages, constant, theme};
pub use button::{
    Button, ButtonAction, ButtonActions, ButtonContent, ButtonDetails, ButtonLayout, ButtonPos,
    ButtonStyle, ButtonStyleSheet,
};
pub use button_controller::{AutomaticMover, ButtonController, ButtonControllerMsg};
pub use common_messages::CancelConfirmMsg;
pub use error::ErrorScreen;
pub use hold_to_confirm::{HoldToConfirm, HoldToConfirmMsg};
pub use input_methods::{
    choice::{Choice, ChoiceControls, ChoiceFactory, ChoiceMsg, ChoicePage},
    choice_item::ChoiceItem,
};
pub use loader::{Loader, LoaderMsg, LoaderStyle, LoaderStyleSheet, ProgressLoader};
pub use result::ResultScreen;
pub use welcome_screen::WelcomeScreen;

#[cfg(all(feature = "micropython", feature = "translations"))]
mod address_details;
mod changing_text;
#[cfg(feature = "translations")]
mod coinjoin_progress;
mod flow;
mod flow_pages;
mod frame;
#[cfg(feature = "micropython")]
mod homescreen;
#[cfg(feature = "translations")]
mod page;
mod progress;
mod scrollbar;
#[cfg(feature = "translations")]
mod share_words;
mod show_more;
mod title;

#[cfg(all(feature = "micropython", feature = "translations"))]
pub use address_details::AddressDetails;

pub use changing_text::ChangingTextLine;
#[cfg(feature = "translations")]
pub use coinjoin_progress::CoinJoinProgress;
pub use flow::Flow;
pub use flow_pages::{FlowPages, Page};
pub use frame::{Frame, ScrollableContent, ScrollableFrame};
#[cfg(feature = "micropython")]
pub use homescreen::{check_homescreen_format, ConfirmHomescreen, Homescreen, Lockscreen};
#[cfg(feature = "translations")]
pub use input_methods::{
    number_input::NumberInput,
    passphrase::PassphraseEntry,
    pin::PinEntry,
    simple_choice::SimpleChoice,
    wordlist::{WordlistEntry, WordlistType},
};
#[cfg(feature = "translations")]
pub use page::ButtonPage;
pub use progress::Progress;
pub use scrollbar::ScrollBar;
#[cfg(feature = "translations")]
pub use share_words::ShareWords;
pub use show_more::{CancelInfoConfirmMsg, ShowMore};
