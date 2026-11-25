# NAOMI TUI — Module Development Guide

Adding a new page to `naomi-tui` does not require modifying the application core (`main.rs`, `nav.rs`, `events.rs`, `ui.rs`, or `terminal.rs`).

## 1. Create a module file

Add `p07/src/modules/my_page.rs` implementing `PageModule`:

```rust
use crossterm::event::{KeyCode, KeyEvent};
use ratatui::layout::Rect;
use ratatui::widgets::Paragraph;
use ratatui::Frame;

use crate::modules::PageModule;
use crate::theme::Theme;

#[derive(Default)]
pub struct MyPage;

impl PageModule for MyPage {
    fn title(&self) -> &str {
        "My Page"
    }

    fn render(&self, frame: &mut Frame, area: Rect, _focused: bool, _theme: &Theme) {
        frame.render_widget(Paragraph::new("Hello from My Page"), area);
    }

    fn handle_key(&mut self, key: KeyEvent) -> Option<String> {
        match key.code {
            KeyCode::Char('r') => Some("Refreshed".to_string()),
            _ => None,
        }
    }
}
```

## 2. Register the module

In `p07/src/modules/mod.rs`:
1. Add `pub mod my_page;`
2. Push `Box::new(my_page::MyPage::default())` in `default_modules()`.

## 3. Customize theme/layout without recompiling

Edit `/etc/boros/tui-theme.conf` (or pass `--theme /path/to/file`) to adjust `header_title`, `accent`, `highlight_bg`, `highlight_fg`, `border`, `text`, `muted`, and `menu_width`.
