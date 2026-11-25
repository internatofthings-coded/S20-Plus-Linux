pub mod example;
pub mod placeholder;

use crossterm::event::KeyEvent;
use ratatui::layout::Rect;
use ratatui::Frame;

use crate::theme::Theme;

/// Contract for independently editable NAOMI TUI pages.
/// Adding a new page requires only implementing this trait and registering it in `default_modules()`.
pub trait PageModule {
    fn title(&self) -> &str;
    fn render(&self, frame: &mut Frame, area: Rect, focused: bool, theme: &Theme);
    fn handle_key(&mut self, _key: KeyEvent) -> Option<String> {
        None
    }
}

pub fn default_modules() -> Vec<Box<dyn PageModule>> {
    vec![
        Box::new(placeholder::PlaceholderModule::new(
            "Overview",
            "Reserved for future NAOMI system overview module.",
        )),
        Box::new(placeholder::PlaceholderModule::new(
            "System",
            "Reserved for future system status and telemetry module.",
        )),
        Box::new(placeholder::PlaceholderModule::new(
            "Settings",
            "Reserved for future configuration and theme settings.",
        )),
        Box::new(example::ExampleModule::default()),
    ]
}
