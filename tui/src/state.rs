#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Focus {
    Menu,
    Content,
}

#[derive(Debug)]
pub struct AppState {
    pub selected_index: usize,
    pub module_count: usize,
    pub focus: Focus,
    pub show_help: bool,
    pub should_quit: bool,
    pub status_hint: String,
}

impl AppState {
    pub fn new(module_count: usize) -> Self {
        Self {
            selected_index: 0,
            module_count,
            focus: Focus::Menu,
            show_help: false,
            should_quit: false,
            status_hint: "Ready".to_string(),
        }
    }

    pub fn select_next(&mut self) {
        if self.module_count > 0 {
            self.selected_index = (self.selected_index + 1) % self.module_count;
        }
    }

    pub fn select_prev(&mut self) {
        if self.module_count > 0 {
            self.selected_index = (self.selected_index + self.module_count - 1) % self.module_count;
        }
    }

    pub fn toggle_focus(&mut self) {
        self.focus = match self.focus {
            Focus::Menu => Focus::Content,
            Focus::Content => Focus::Menu,
        };
    }
}
