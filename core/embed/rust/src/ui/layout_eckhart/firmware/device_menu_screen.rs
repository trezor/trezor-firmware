use crate::ui::{
    component::{base::AttachType, Component, Event, EventCtx},
    geometry::Rect,
    layout_eckhart::{
        component::Button,
        constant::SCREEN,
        firmware::{VerticalMenuScreen, VerticalMenuScreenMsg, MENU_MAX_ITEMS},
    },
    shape::Renderer,
};

use heapless::Vec;

// Max number of menu screens
const MAX_MENUS: usize = 5;

type VerticalMenus = Vec<Button, MAX_MENUS>;

pub enum DeviceMenuMsg {
    Selected(usize),
    /// Right header button clicked
    Close,
}

/// Linear map of vertical menus.
pub struct DeviceMenuScreen {
    /// Bounds of the menu screen
    bounds: Rect,
    /// Index of the currently active menu
    active_menu: usize,
    ///  Stack of parent menus for back navigation
    menu_parents: Vec<usize, MAX_MENUS>,
    /// Stack of menu screens and their children
    menu_stack: Vec<(VerticalMenuScreen, Vec<Option<usize>, MENU_MAX_ITEMS>), 5>,
}

impl DeviceMenuScreen {
    pub fn empty() -> Self {
        Self {
            bounds: Rect::zero(),
            active_menu: 0, // Start with the first menu by default
            menu_stack: Vec::new(),
            menu_parents: Vec::new(),
        }
    }

    // Add an internal menu screen with children and return the index of the new
    // menu within the stack. The children are optional indices of the sub-menus in
    // the stack
    pub fn add_inner_menu(
        &mut self,
        menu: VerticalMenuScreen,
        children: Vec<Option<usize>, MENU_MAX_ITEMS>,
    ) -> usize {
        unwrap!(self.menu_stack.push((menu, children)));
        self.menu_stack.len() - 1
    }

    // Add a leaf menu screen (without any children)
    pub fn add_leaf_menu(&mut self, menu: VerticalMenuScreen) -> usize {
        let mut children = Vec::new();
        for _ in 0..MENU_MAX_ITEMS {
            unwrap!(children.push(None));
        }

        self.add_inner_menu(menu, children)
    }

    // Set the index of the active menu
    pub fn set_active_menu(&mut self, menu: usize) {
        assert!(menu < self.menu_stack.len());
        self.active_menu = menu;
    }

    // Navigate to a different menu based on selection.
    fn handle_menu_selection(&mut self, ctx: &mut EventCtx, index: usize) -> Option<DeviceMenuMsg> {
        if self.menu_stack[self.active_menu].1[index].is_some() {
            unwrap!(self.menu_parents.push(self.active_menu));
            self.active_menu = self.menu_stack[self.active_menu].1[index].unwrap();
            self.place(self.bounds);
            self.menu_stack[self.active_menu].0.update_menu(ctx);
        }
        None
    }

    // Handle back navigation to previously active menu
    fn handle_back_navigation(&mut self) -> Option<DeviceMenuMsg> {
        if self.menu_parents.is_empty() {
            Some(DeviceMenuMsg::Close)
        } else {
            self.active_menu = self.menu_parents.pop().unwrap();
            self.place(self.bounds);
            None
        }
    }
}

impl Component for DeviceMenuScreen {
    type Msg = DeviceMenuMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // assert full screen
        debug_assert_eq!(bounds.height(), SCREEN.height());
        debug_assert_eq!(bounds.width(), SCREEN.width());

        self.bounds = bounds;
        // Place the active menu
        self.menu_stack[self.active_menu].0.place(bounds);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // Update the menu when the screen is attached
        if let Event::Attach(AttachType::Initial) = event {}
        // Handle the event for the active menu
        match self.menu_stack[self.active_menu].0.event(ctx, event) {
            Some(VerticalMenuScreenMsg::Selected(index)) => {
                // Navigate to the selected menu (if any)
                return self.handle_menu_selection(ctx, index);
            }
            Some(VerticalMenuScreenMsg::Back) => {
                return self.handle_back_navigation();
            }
            Some(VerticalMenuScreenMsg::Close) => {
                return Some(DeviceMenuMsg::Close);
            }
            _ => {}
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        // Render the active menu if any
        self.menu_stack[self.active_menu].0.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for DeviceMenuScreen {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("DeviceMenuScreen");
    }
}
