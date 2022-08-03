use crate::ui::{
    component::{Child, Component, Event, EventCtx, Pad},
    geometry::{Offset, Point, Rect},
};

use super::{common, theme, ButtonController, ButtonControllerMsg, ButtonPos, FlowPage, FlowPages};
use heapless::Vec;

pub enum FlowMsg {
    Confirmed,
    Cancelled,
}

pub struct Flow<T, const N: usize> {
    pages: Vec<FlowPages<T>, N>,
    common_title: Option<T>,
    pad: Pad,
    buttons: Child<ButtonController<&'static str>>,
    page_counter: u8,
}

impl<T, const N: usize> Flow<T, N>
where
    T: AsRef<str>,
    T: Clone,
{
    pub fn new(pages: Vec<FlowPages<T>, N>) -> Self {
        let initial_btn_layout = pages[0].btn_layout();

        Self {
            pages,
            common_title: None,
            pad: Pad::with_background(theme::BG),
            buttons: Child::new(ButtonController::new(initial_btn_layout)),
            page_counter: 0,
        }
    }

    /// Adding a common title to all pages. The title will not be colliding
    /// with the page content, as the content will be offset.
    pub fn with_common_title(mut self, title: T) -> Self {
        self.common_title = Some(title);
        self
    }

    /// Rendering the whole page.
    fn paint_page(&mut self) {
        // Optionally drawing the header.
        // In that case offsetting the whole page by the height of the header.
        // TODO: print statements uncovered that this is being called
        // also when the button is just pressed, which is wasteful
        // (and also repeatedly when the HTC was being pressed)
        const TOP_LEFT: Point = Point::zero();
        if let Some(title) = &self.common_title {
            let y_offset = common::paint_header(TOP_LEFT, title, None);
            self.current_choice().paint(TOP_LEFT + Offset::y(y_offset));
        } else {
            self.current_choice().paint(TOP_LEFT);
        }
    }

    /// Setting current buttons, and clearing.
    fn update(&mut self, ctx: &mut EventCtx) {
        self.set_buttons(ctx);
        self.clear(ctx);
    }

    /// Clearing the whole area and requesting repaint.
    fn clear(&mut self, ctx: &mut EventCtx) {
        self.pad.clear();
        ctx.request_paint();
    }

    fn last_page_index(&self) -> u8 {
        self.pages.len() as u8 - 1
    }

    fn has_previous_choice(&self) -> bool {
        self.page_counter > 0
    }

    fn has_next_choice(&self) -> bool {
        self.page_counter < self.last_page_index()
    }

    fn current_choice(&mut self) -> &mut FlowPages<T> {
        &mut self.pages[self.page_counter as usize]
    }

    fn decrease_page_counter(&mut self) {
        self.page_counter -= 1;
    }

    fn increase_page_counter(&mut self) {
        self.page_counter += 1;
    }

    /// Updating the visual state of the buttons after each event.
    /// All three buttons are handled based upon the current choice.
    /// If defined in the current choice, setting their text,
    /// whether they are long-pressed, and painting them.
    ///
    /// NOTE: ButtonController is handling the painting, and
    /// it will not repaint the buttons unless some of them changed.
    fn set_buttons(&mut self, ctx: &mut EventCtx) {
        let btn_layout = self.current_choice().btn_layout();
        self.buttons.mutate(ctx, |ctx, buttons| {
            buttons.set(ctx, btn_layout);
        });
    }
}

impl<T, const N: usize> Component for Flow<T, N>
where
    T: AsRef<str>,
    T: Clone,
{
    type Msg = FlowMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (content_area, button_area) = bounds.split_bottom(theme::BUTTON_HEIGHT);
        self.pad.place(content_area);
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let button_event = self.buttons.event(ctx, event);

        if let Some(ButtonControllerMsg::Triggered(pos)) = button_event {
            match pos {
                ButtonPos::Left => {
                    if self.has_previous_choice() {
                        // Clicked BACK. Decrease the page counter.
                        self.decrease_page_counter();
                        self.update(ctx);
                    } else {
                        // Triggered LEFTmost button. Send event
                        self.clear(ctx);
                        return Some(FlowMsg::Cancelled);
                    }
                }
                ButtonPos::Right => {
                    if self.has_next_choice() {
                        // Clicked NEXT. Increase the page counter.
                        self.increase_page_counter();
                        self.update(ctx);
                    } else {
                        // Triggered RIGHTmost button. Send event
                        self.clear(ctx);
                        return Some(FlowMsg::Confirmed);
                    }
                }
                _ => {}
            }
        };
        None
    }

    fn paint(&mut self) {
        // TODO: might put horizontal scrollbar at the top right
        self.pad.paint();
        self.buttons.paint();
        self.paint_page();
    }
}

#[cfg(feature = "ui_debug")]
impl<T, const N: usize> crate::trace::Trace for Flow<T, N> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Flow");
        t.close();
    }
}
