use crate::{
    strutil::TString,
    translations::TR,
    ui::{
        component::{swipe_detect::SwipeSettings, Component, SwipeDirection},
        flow::{Swipable, SwipePage},
    },
};

use super::{
    Frame, FrameMsg, InternallySwipable as _, PagedVerticalMenu, SwipeContent,
    VerticalMenuChoiceMsg,
};

#[derive(Copy, Clone, PartialEq, Eq)]
pub enum ConfirmFido {
    Intro,
    ChooseCredential,
    Details,
    Tap,
    Menu,
}

/// Wrapper that updates `Footer` content whenever page is changed.
pub struct ChooseCredential<F: Fn(usize) -> TString<'static>>(
    Frame<SwipeContent<SwipePage<PagedVerticalMenu<F>>>>,
);

impl<F: Fn(usize) -> TString<'static>> ChooseCredential<F> {
    pub fn new(label_fn: F, num_accounts: usize) -> Self {
        let content_choose_credential = Frame::left_aligned(
            TR::fido__title_select_credential.into(),
            SwipeContent::new(SwipePage::vertical(PagedVerticalMenu::new(
                num_accounts,
                label_fn,
            ))),
        )
        .with_subtitle(TR::fido__title_for_authentication.into())
        .with_menu_button()
        .with_footer_page_hint(
            TR::fido__more_credentials.into(),
            TR::buttons__go_back.into(),
            TR::instructions__swipe_up.into(),
            TR::instructions__swipe_down.into(),
        )
        .with_swipe(SwipeDirection::Down, SwipeSettings::default())
        .with_swipe(SwipeDirection::Right, SwipeSettings::immediate())
        .with_vertical_pages();

        Self(content_choose_credential)
    }
}

impl<F: Fn(usize) -> TString<'static>> Component for ChooseCredential<F> {
    type Msg = FrameMsg<VerticalMenuChoiceMsg>;

    fn place(&mut self, bounds: crate::ui::geometry::Rect) -> crate::ui::geometry::Rect {
        self.0.place(bounds)
    }

    fn event(
        &mut self,
        ctx: &mut crate::ui::component::EventCtx,
        event: crate::ui::component::Event,
    ) -> Option<Self::Msg> {
        let msg = self.0.event(ctx, event);
        let current_page = self.0.inner().inner().inner().current_page();

        self.0.update_footer_counter(
            ctx,
            current_page,
            Some(self.0.inner().inner().inner().num_pages()),
        );
        msg
    }

    fn paint(&mut self) {
        self.0.paint()
    }

    fn render<'s>(&'s self, target: &mut impl crate::ui::shape::Renderer<'s>) {
        self.0.render(target)
    }
}

impl<F: Fn(usize) -> TString<'static>> Swipable for ChooseCredential<F> {
    fn get_swipe_config(&self) -> crate::ui::component::swipe_detect::SwipeConfig {
        self.0.get_swipe_config()
    }

    fn get_internal_page_count(&self) -> usize {
        self.0.get_internal_page_count()
    }
}

#[cfg(feature = "ui_debug")]
impl<F: Fn(usize) -> TString<'static>> crate::trace::Trace for ChooseCredential<F> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.0.trace(t)
    }
}
