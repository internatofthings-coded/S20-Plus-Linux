use crossterm::event::{KeyCode, KeyEvent};
use ratatui::layout::Rect;
use ratatui::text::{Line, Span};
use ratatui::widgets::{Paragraph, Wrap};
use ratatui::Frame;

use crate::modules::PageModule;
use crate::theme::Theme;

/// Minimal example module demonstrating module-local state and key handling.
#[derive(Default)]
pub struct ExampleModule {
    counter: u32,
}

impl PageModule for ExampleModule {
    fn title(&self) -> &str {
        "Example"
    }

    fn render(&self, frame: &mut Frame, area: Rect, focused: bool, theme: &Theme) {
        let lines = vec![
            Line::from(Span::styled("Example Module", theme.header_style())),
            Line::from(""),
            Line::from("Demonstrates how a future page owns its own state and input."),
            Line::from(format!("Counter: {}", self.counter)),
            Line::from(""),
            Line::from(Span::styled(
                if focused {
                    "Press Space/+ to increment, r to reset, Esc for menu."
                } else {
                    "Press Enter to focus this module."
                },
                theme.muted_style(),
            )),
        ];
        let body = Paragraph::new(lines).wrap(Wrap { trim: true });
        frame.render_widget(body, area);
    }

    fn handle_key(&mut self, key: KeyEvent) -> Option<String> {
        match key.code {
            KeyCode::Char(' ') | KeyCode::Char('+') | KeyCode::Up => {
                self.counter = self.counter.saturating_add(1);
                Some(format!("Example counter = {}", self.counter))
            }
            KeyCode::Char('r') => {
                self.counter = 0;
                Some("Example counter reset".to_string())
            }
            _ => None,
        }
    }
}
