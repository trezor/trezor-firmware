use crate::ui::{
    component::{Child, Component, Event, EventCtx, Pad},
    geometry::Rect,
};

use super::{theme, ButtonController, ButtonControllerMsg, ButtonPos, FlowPage, FlowPages};
use heapless::Vec;

pub enum FlowMsg {
    Confirmed,
    Cancelled,
}

pub struct Flow<const N: usize> {
    pages: Vec<FlowPages, N>,
    pad: Pad,
    buttons: Child<ButtonController<&'static str>>,
    page_counter: u8,
}

impl<const N: usize> Flow<N> {
    pub fn new(pages: Vec<FlowPages, N>) -> Self {
        let initial_btn_layout = pages[0].btn_layout();

        Self {
            pages,
            pad: Pad::with_background(theme::BG),
            buttons: Child::new(ButtonController::new(initial_btn_layout)),
            page_counter: 0,
        }
    }

    fn paint_page(&mut self) {
        self.show_current_choice();
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

    fn current_choice(&mut self) -> &mut FlowPages {
        &mut self.pages[self.page_counter as usize]
    }

    fn show_current_choice(&mut self) {
        self.pages[self.page_counter as usize].paint();
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

impl<const N: usize> Component for Flow<N> {
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
        // Also, top left corner could be used for some short title
        self.pad.paint();
        self.buttons.paint();
        self.paint_page();
    }
}

#[cfg(feature = "ui_debug")]
impl<const N: usize> crate::trace::Trace for Flow<N> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Flow");
        t.close();
    }
}
