use crate::{
    micropython::buffer::StrBuffer,
    ui::{
        component::{Child, Component, Event, EventCtx, Pad},
        geometry::Rect,
    },
};

use super::{
    common, theme, ButtonAction, ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos,
    FlowPages, Page,
};

/// To be returned directly from Flow.
pub enum FlowMsg {
    Confirmed,
    Cancelled,
}

// TODO: consider each FlowPage having the ability
// to handle custom actions triggered by some btn.

pub struct Flow<F, const M: usize> {
    pages: FlowPages<F, M>,
    current_page: Page<M>,
    common_title: Option<StrBuffer>,
    content_area: Rect,
    pad: Pad,
    buttons: Child<ButtonController<&'static str>>,
    page_counter: u8,
}

impl<F, const M: usize> Flow<F, M>
where
    F: Fn(u8) -> Page<M>,
{
    pub fn new(pages: FlowPages<F, M>) -> Self {
        let current_page = pages.get(0);
        Self {
            pages,
            current_page,
            common_title: None,
            content_area: Rect::zero(),
            pad: Pad::with_background(theme::BG),
            // Setting empty layout for now, we do not yet know how many sub-pages the first page
            // has. Initial button layout will be set in `place()` after we can call
            // `content.page_count()`.
            buttons: Child::new(ButtonController::new(ButtonLayout::empty())),
            page_counter: 0,
        }
    }

    /// Adding a common title to all pages. The title will not be colliding
    /// with the page content, as the content will be offset.
    pub fn with_common_title(mut self, title: StrBuffer) -> Self {
        self.common_title = Some(title);
        self
    }

    /// Placing current page, setting current buttons and clearing.
    fn update(&mut self, ctx: &mut EventCtx, get_new_page: bool) {
        if get_new_page {
            self.current_page = self.pages.get(self.page_counter);
        }
        self.current_page.place(self.content_area);
        self.set_buttons(ctx);
        self.clear(ctx);
    }

    /// Clearing the whole area and requesting repaint.
    fn clear(&mut self, ctx: &mut EventCtx) {
        self.pad.clear();
        ctx.request_paint();
    }

    /// Going to the previous page.
    fn go_to_prev_page(&mut self, ctx: &mut EventCtx) {
        self.page_counter -= 1;
        self.update(ctx, true);
    }

    /// Going to the next page.
    fn go_to_next_page(&mut self, ctx: &mut EventCtx) {
        self.page_counter += 1;
        self.update(ctx, true);
    }

    /// Going to page by its absolute index.
    /// Negative index means counting from the end.
    fn go_to_page_absolute(&mut self, index: i16, ctx: &mut EventCtx) {
        if index < 0 {
            self.page_counter = (self.pages.count() as i16 + index) as u8;
        } else {
            self.page_counter = index as u8;
        }
        self.update(ctx, true);
    }

    /// Jumping to another page relative to the current one.
    fn go_to_page_relative(&mut self, jump: i16, ctx: &mut EventCtx) {
        self.page_counter = (self.page_counter as i16 + jump) as u8;
        self.update(ctx, true);
    }

    /// Updating the visual state of the buttons after each event.
    /// All three buttons are handled based upon the current choice.
    /// If defined in the current choice, setting their text,
    /// whether they are long-pressed, and painting them.
    ///
    /// NOTE: ButtonController is handling the painting, and
    /// it will not repaint the buttons unless some of them changed.
    fn set_buttons(&mut self, ctx: &mut EventCtx) {
        let btn_layout = self.current_page.btn_layout();
        self.buttons.mutate(ctx, |_ctx, buttons| {
            buttons.set(btn_layout);
        });
    }

    /// When current choice contains paginated content, it may use the button
    /// event to just paginate itself.
    fn event_consumed_by_current_choice(&mut self, ctx: &mut EventCtx, pos: ButtonPos) -> bool {
        if matches!(pos, ButtonPos::Left) && self.current_page.has_prev_page() {
            self.current_page.go_to_prev_page();
            self.update(ctx, false);
            true
        } else if matches!(pos, ButtonPos::Right) && self.current_page.has_next_page() {
            self.current_page.go_to_next_page();
            self.update(ctx, false);
            true
        } else {
            false
        }
    }
}

impl<F, const M: usize> Component for Flow<F, M>
where
    F: Fn(u8) -> Page<M>,
{
    type Msg = FlowMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (title_content_area, button_area) = bounds.split_bottom(theme::BUTTON_HEIGHT);
        // Accounting for possible title
        let content_area = if self.common_title.is_some() {
            title_content_area
                .split_top(theme::FONT_HEADER.line_height())
                .1
        } else {
            title_content_area
        };
        self.content_area = content_area;

        // We finally found how long is the first page, and can set its button layout.
        self.current_page.place(content_area);
        self.buttons = Child::new(ButtonController::new(self.current_page.btn_layout()));

        self.pad.place(title_content_area);
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let button_event = self.buttons.event(ctx, event);

        // Do something when a button was triggered
        // and we have some action connected with it
        if let Some(ButtonControllerMsg::Triggered(pos)) = button_event {
            // When there is a previous or next screen in the current flow,
            // handle that first and in case it triggers, then do not continue
            if self.event_consumed_by_current_choice(ctx, pos) {
                return None;
            }

            let actions = self.current_page.btn_actions();
            let action = actions.get_action(pos);
            if let Some(action) = action {
                match action {
                    ButtonAction::PrevPage => {
                        self.go_to_prev_page(ctx);
                        return None;
                    }
                    ButtonAction::NextPage => {
                        self.go_to_next_page(ctx);
                        return None;
                    }
                    ButtonAction::GoToIndex(index) => {
                        self.go_to_page_absolute(index, ctx);
                        return None;
                    }
                    ButtonAction::MovePageRelative(jump) => {
                        self.go_to_page_relative(jump, ctx);
                        return None;
                    }
                    ButtonAction::Cancel => return Some(FlowMsg::Cancelled),
                    ButtonAction::Confirm => return Some(FlowMsg::Confirmed),
                    ButtonAction::Select => {}
                    ButtonAction::Action(_) => {}
                }
            }
        };
        None
    }

    fn paint(&mut self) {
        // TODO: might put horizontal scrollbar at the top right
        // (not compatible with longer/centered titles)
        self.pad.paint();
        if let Some(title) = &self.common_title {
            common::paint_header_centered(title, self.content_area);
        }
        self.current_page.paint();
        self.buttons.paint();
    }
}

#[cfg(feature = "ui_debug")]
use heapless::String;

#[cfg(feature = "ui_debug")]
impl<F, const M: usize> crate::trace::Trace for Flow<F, M>
where
    F: Fn(u8) -> Page<M>,
{
    /// Accounting for the possibility that button is connected with the
    /// currently paginated flow_page (only Prev or Next in that case).
    fn get_btn_action(&self, pos: ButtonPos) -> String<25> {
        if matches!(pos, ButtonPos::Left) && self.current_page.has_prev_page() {
            ButtonAction::PrevPage.string()
        } else if matches!(pos, ButtonPos::Right) && self.current_page.has_next_page() {
            ButtonAction::NextPage.string()
        } else {
            let btn_actions = self.current_page.btn_actions();

            match btn_actions.get_action(pos) {
                Some(action) => action.string(),
                None => ButtonAction::empty(),
            }
        }
    }

    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Flow");
        t.kw_pair("flow_page", inttostr!(self.page_counter));
        t.kw_pair("flow_page_count", inttostr!(self.pages.count()));

        self.report_btn_actions(t);

        if let Some(title) = &self.common_title {
            t.title(title.as_ref());
        }
        t.field("content_area", &self.content_area);
        t.field("buttons", &self.buttons);
        t.field("flow_page", &self.current_page);
        t.close()
    }
}
