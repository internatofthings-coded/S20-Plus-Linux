use ratatui::layout::Rect;
use ratatui::text::{Line, Span};
use ratatui::widgets::{Paragraph, Wrap};
use ratatui::Frame;

use crate::modules::PageModule;
use crate::theme::Theme;

pub struct PlaceholderModule {
    title: String,
    description: String,
}

impl PlaceholderModule {
    pub fn new(title: impl Into<String>, description: impl Into<String>) -> Self {
        Self {
            title: title.into(),
            description: description.into(),
        }
    }
}

impl PageModule for PlaceholderModule {
    fn title(&self) -> &str {
        &self.title
    }

    fn render(&self, frame: &mut Frame, area: Rect, focused: bool, theme: &Theme) {
        let focus_label = if focused {
            "ACTIVE (press Esc to return to Menu)"
        } else {
            "PREVIEW (press Enter or Tab to focus)"
        };
        let lines = vec![
            Line::from(Span::styled(&self.title, theme.header_style())),
            Line::from(""),
            Line::from(self.description.as_str()),
            Line::from(""),
            Line::from(Span::styled(focus_label, theme.muted_style())),
        ];
        let body = Paragraph::new(lines).wrap(Wrap { trim: true });
        frame.render_widget(body, area);
    }
}
