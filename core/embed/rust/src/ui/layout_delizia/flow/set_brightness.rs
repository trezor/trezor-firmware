use core::sync::atomic::{AtomicU8, Ordering};

use crate::{
    error::Error,
    storage,
    translations::TR,
    trezorhal::display,
    ui::{
        component::{swipe_detect::SwipeSettings, EventCtx, FlowMsg},
        flow::{base::Decision, FlowStore, GcBoxFlowComponent, SwipeFlow},
        geometry::Direction,
        layout_delizia::component::VerticalMenuChoiceMsg,
    },
};

use super::super::{
    component::{
        number_input_slider::{NumberInputSliderDialog, NumberInputSliderDialogMsg},
        Footer, Frame, PromptMsg, PromptScreen, StatusScreen, SwipeContent, VerticalMenu,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum SetBrightness {
    Slider,
    Menu,
    Confirm,
    Confirmed,
}

static BRIGHTNESS: AtomicU8 = AtomicU8::new(0);

fn footer_update_fn(
    content: &NumberInputSliderDialog,
    ctx: &mut EventCtx,
    footer: &mut Footer<'static>,
) {
    if content.value() == content.init_value() || content.touching() {
        footer.update_instruction(ctx, TR::instructions__swipe_horizontally);
        footer.update_description(ctx, TR::setting__adjust);
    } else {
        footer.update_instruction(ctx, TR::instructions__tap_to_continue);
        footer.update_description(ctx, TR::setting__apply);
    }
}

pub fn new_set_brightness(brightness: Option<u8>) -> Result<SwipeFlow, Error> {
    let brightness = brightness.unwrap_or(theme::backlight::get_backlight_normal());
    let content_slider = Frame::left_aligned(
        TR::brightness__title.into(),
        NumberInputSliderDialog::new(
            theme::backlight::get_backlight_min() as u16,
            theme::backlight::get_backlight_max() as u16,
            brightness as u16,
        ),
    )
    .with_subtitle(TR::homescreen__settings_subtitle.into())
    .with_menu_button()
    .with_swipe(Direction::Up, SwipeSettings::default())
    .with_footer(
        TR::instructions__swipe_horizontally.into(),
        Some(TR::setting__adjust.into()),
    )
    .register_footer_update_fn(footer_update_fn)
    .map(|msg| match msg {
        NumberInputSliderDialogMsg::Changed(n) => {
            display::backlight(n as _);
            BRIGHTNESS.store(n as u8, Ordering::Relaxed);
            None
        }
    });

    let content_menu = Frame::left_aligned(
        "".into(),
        VerticalMenu::empty().danger(theme::ICON_CANCEL, TR::buttons__cancel.into()),
    )
    .with_cancel_button()
    .map(map_to_choice);

    let content_confirm = Frame::left_aligned(
        TR::brightness__change_title.into(),
        SwipeContent::new(PromptScreen::new_tap_to_confirm()),
    )
    .with_footer(TR::instructions__tap_to_confirm.into(), None)
    .with_menu_button()
    .with_swipe(Direction::Down, SwipeSettings::default())
    .map(move |msg| match msg {
        PromptMsg::Confirmed => {
            let _ = storage::set_brightness(BRIGHTNESS.load(Ordering::Relaxed));
            Some(FlowMsg::Confirmed)
        }
        _ => None,
    });

    let content_confirmed = Frame::left_aligned(
        TR::words__title_success.into(),
        SwipeContent::new(StatusScreen::new_success(
            TR::brightness__changed_title.into(),
        ))
        .with_no_attach_anim(),
    )
    .with_swipeup_footer(None)
    .with_result_icon(theme::ICON_BULLET_CHECKMARK, theme::GREEN_LIGHT)
    .map(move |_msg| Some(FlowMsg::Confirmed));

    let mut store = FlowStore::new();

    let slider = store.add(GcBoxFlowComponent::alloc(content_slider)?);
    let menu = store.add(GcBoxFlowComponent::alloc(content_menu)?);
    let confirm = store.add(GcBoxFlowComponent::alloc(content_confirm)?);
    let confirmed = store.add(GcBoxFlowComponent::alloc(content_confirmed)?);

    store.on_swipe(slider, Direction::Up, confirm.swipe_up());
    store.on_swipe(confirm, Direction::Down, slider.swipe_down());
    store.on_swipe(confirmed, Direction::Up, FlowMsg::Confirmed.into());

    store.on_event(slider, FlowMsg::Info, menu.swipe_left());
    store.on_event(menu, FlowMsg::Cancelled, slider.goto());
    store.on_event(menu, FlowMsg::Choice(0), FlowMsg::Cancelled.into());
    store.on_event(confirm, FlowMsg::Confirmed, confirmed.swipe_up());
    store.on_event(confirm, FlowMsg::Info, menu.swipe_left());
    store.on_event(confirmed, FlowMsg::Confirmed, FlowMsg::Confirmed.into());

    SwipeFlow::new(store)
}

fn map_to_choice(msg: VerticalMenuChoiceMsg) -> Option<FlowMsg> {
    match msg {
        VerticalMenuChoiceMsg::Selected(i) => Some(FlowMsg::Choice(i)),
    }
}
