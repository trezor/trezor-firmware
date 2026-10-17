// The bootloader has its own copies of the interactive components (see
// `layout_caesar::bootloader`), so that firmware UI changes cannot reach it
// unnoticed. Everything except the boot and fatal error screens is therefore
// left out of the bootloader build.

mod error;
mod welcome_screen;

pub use error::ErrorScreen;
pub use welcome_screen::WelcomeScreen;

#[cfg(not(feature = "bootloader"))]
mod button;
#[cfg(not(feature = "bootloader"))]
mod button_controller;
#[cfg(not(feature = "bootloader"))]
mod hold_to_confirm;
#[cfg(not(feature = "bootloader"))]
mod input_methods;
#[cfg(not(feature = "bootloader"))]
mod loader;

#[cfg(not(feature = "bootloader"))]
pub use button::{
    Button, ButtonAction, ButtonActions, ButtonContent, ButtonDetails, ButtonLayout, ButtonPos,
};
#[cfg(not(feature = "bootloader"))]
pub use button_controller::{AutomaticMover, ButtonController, ButtonControllerMsg};
#[cfg(not(feature = "bootloader"))]
pub use common_messages::CancelConfirmMsg;
#[cfg(not(feature = "bootloader"))]
pub use hold_to_confirm::{HoldToConfirm, HoldToConfirmMsg};
#[cfg(not(feature = "bootloader"))]
pub use input_methods::choice::{Choice, ChoiceControls, ChoiceFactory, ChoiceMsg, ChoicePage};
#[cfg(not(feature = "bootloader"))]
pub use input_methods::choice_item::ChoiceItem;
#[cfg(not(feature = "bootloader"))]
pub use loader::{Loader, LoaderMsg, LoaderStyle, LoaderStyleSheet, ProgressLoader};

#[cfg(not(feature = "bootloader"))]
use super::{common_messages, constant, theme};

#[cfg(all(feature = "micropython", feature = "translations"))]
mod address_details;
#[cfg(not(feature = "bootloader"))]
mod changing_text;
#[cfg(feature = "translations")]
mod coinjoin_progress;
#[cfg(not(feature = "bootloader"))]
mod flow;
#[cfg(not(feature = "bootloader"))]
mod flow_pages;
#[cfg(not(feature = "bootloader"))]
mod frame;
#[cfg(feature = "micropython")]
mod homescreen;
#[cfg(feature = "translations")]
mod page;
#[cfg(not(feature = "bootloader"))]
mod progress;
#[cfg(not(feature = "bootloader"))]
mod scrollbar;
#[cfg(feature = "translations")]
mod share_words;
#[cfg(not(feature = "bootloader"))]
mod title;

#[cfg(all(feature = "micropython", feature = "translations"))]
pub use address_details::AddressDetails;
#[cfg(not(feature = "bootloader"))]
pub use changing_text::ChangingTextLine;
#[cfg(feature = "translations")]
pub use coinjoin_progress::CoinJoinProgress;
#[cfg(not(feature = "bootloader"))]
pub use flow::Flow;
#[cfg(not(feature = "bootloader"))]
pub use flow_pages::{FlowPages, Page};
#[cfg(not(feature = "bootloader"))]
pub use frame::{Frame, ScrollableFrame};
#[cfg(feature = "micropython")]
pub use homescreen::{check_homescreen_format, ConfirmHomescreen, Homescreen, Lockscreen};
#[cfg(feature = "translations")]
pub use input_methods::{
    number_input::{NumberInput, NumberInputAction},
    passphrase::PassphraseEntry,
    pin::PinEntry,
    simple_choice::{SimpleChoice, MAX_LENGTH as SIMPLE_CHOICE_MAX_LENGTH},
    wordlist::{WordlistEntry, WordlistType},
};
#[cfg(feature = "translations")]
pub use page::{ButtonPage, MenuNav};
#[cfg(not(feature = "bootloader"))]
pub use progress::Progress;
#[cfg(not(feature = "bootloader"))]
pub use scrollbar::ScrollBar;
#[cfg(feature = "translations")]
pub use share_words::ShareWords;
