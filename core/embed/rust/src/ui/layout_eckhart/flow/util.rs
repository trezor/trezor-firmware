use crate::{
    error::Error,
    maybe_trace::MaybeTrace,
    ui::{
        component::Component,
        flow::{
            base::{Decision, DecisionBuilder},
            FlowController, FlowMsg, Swipable, SwipeFlow,
        },
        geometry::Direction,
    },
};

enum SinglePage {
    Show,
}

impl FlowController for SinglePage {
    #[inline]
    fn index(&'static self) -> usize {
        0
    }

    fn handle_swipe(&'static self, _direction: Direction) -> Decision {
        self.do_nothing()
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        self.return_msg(msg)
    }
}

pub fn single_page<T>(layout: T) -> Result<SwipeFlow, Error>
where
    T: Component<Msg = FlowMsg> + Swipable + MaybeTrace + 'static,
{
    let mut flow = SwipeFlow::new(&SinglePage::Show)?;
    flow.add_page(&SinglePage::Show, layout)?;
    Ok(flow)
}
