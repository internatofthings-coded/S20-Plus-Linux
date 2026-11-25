use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::Modifier;
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Clear, List, ListItem, ListState, Paragraph, Wrap};
use ratatui::Frame;

use crate::modules::PageModule;
use crate::state::{AppState, Focus};
use crate::theme::Theme;

pub fn render(frame: &mut Frame, state: &AppState, modules: &[Box<dyn PageModule>], theme: &Theme) {
    let area = frame.area();
    let vertical = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Min(5),
            Constraint::Length(1),
        ])
        .split(area);

    render_header(frame, vertical[0], state, theme);
    render_body(frame, vertical[1], state, modules, theme);
    render_footer(frame, vertical[2], state, theme);

    if state.show_help {
        render_help_popup(frame, area, theme);
    }
}

fn render_header(frame: &mut Frame, area: Rect, state: &AppState, theme: &Theme) {
    let title = if area.width >= 72 {
        format!(
            " {} // Interactive Terminal Foundation  [{}]",
            theme.header_title, state.status_hint
        )
    } else if area.width >= 44 {
        format!(" {} // TUI  [{}]", theme.header_title, state.status_hint)
    } else {
        format!(" {}", theme.header_title)
    };

    let header = Paragraph::new(Line::from(Span::styled(title, theme.header_style())))
        .block(Block::default().borders(Borders::ALL).border_style(theme.border_style(false)));
    frame.render_widget(header, area);
}

fn render_body(
    frame: &mut Frame,
    area: Rect,
    state: &AppState,
    modules: &[Box<dyn PageModule>],
    theme: &Theme,
) {
    // Responsive layout: side-by-side on wide/medium terminals, stacked on narrow mobile screens.
    let (menu_area, content_area) = if area.width >= 56 {
        let chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Length(theme.menu_width.min(area.width / 3)),
                Constraint::Min(20),
            ])
            .split(area);
        (chunks[0], chunks[1])
    } else {
        let menu_h = (modules.len() as u16 + 2).min(area.height / 2).max(3);
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([Constraint::Length(menu_h), Constraint::Min(3)])
            .split(area);
        (chunks[0], chunks[1])
    };

    let items: Vec<ListItem> = modules
        .iter()
        .map(|m| ListItem::new(format!(" {}", m.title())))
        .collect();

    let mut list_state = ListState::default();
    list_state.select(Some(state.selected_index));

    let menu = List::new(items)
        .block(
            Block::default()
                .title(" Menu ")
                .borders(Borders::ALL)
                .border_style(theme.border_style(state.focus == Focus::Menu)),
        )
        .highlight_style(theme.selected_style())
        .highlight_symbol(">");
    frame.render_stateful_widget(menu, menu_area, &mut list_state);

    let content_block = Block::default()
        .title(
            modules
                .get(state.selected_index)
                .map(|m| format!(" {} ", m.title()))
                .unwrap_or_else(|| " Page ".to_string()),
        )
        .borders(Borders::ALL)
        .border_style(theme.border_style(state.focus == Focus::Content));

    let inner = content_block.inner(content_area);
    frame.render_widget(content_block, content_area);

    if let Some(module) = modules.get(state.selected_index) {
        module.render(frame, inner, state.focus == Focus::Content, theme);
    }
}

fn render_footer(frame: &mut Frame, area: Rect, state: &AppState, theme: &Theme) {
    let controls = if area.width >= 68 {
        match state.focus {
            Focus::Menu => " ↑/↓: Move | Enter: Open | Tab: Focus | ?: Help | Esc/q: Exit to Shell",
            Focus::Content => " Esc: Back to Menu | Tab: Focus | ?: Help | q/Ctrl+C: Exit to Shell",
        }
    } else {
        " ↑/↓ Enter Tab ?:Help Esc/q:Exit"
    };
    let footer = Paragraph::new(Line::from(Span::styled(controls, theme.muted_style())));
    frame.render_widget(footer, area);
}

fn render_help_popup(frame: &mut Frame, area: Rect, theme: &Theme) {
    let popup_w = area.width.saturating_sub(6).min(56).max(24);
    let popup_h = area.height.saturating_sub(4).min(13).max(7);
    let x = area.x + (area.width.saturating_sub(popup_w)) / 2;
    let y = area.y + (area.height.saturating_sub(popup_h)) / 2;
    let rect = Rect::new(x, y, popup_w, popup_h);

    frame.render_widget(Clear, rect);
    let lines = vec![
        Line::from(Span::styled(
            "NAOMI TUI Controls",
            theme.header_style().add_modifier(Modifier::UNDERLINED),
        )),
        Line::from(""),
        Line::from("  ↑ / ↓ (or j/k)   Navigate menu"),
        Line::from("  Enter            Open selected page"),
        Line::from("  Tab / Shift+Tab  Switch Menu <-> Page focus"),
        Line::from("  Esc              Back to Menu (or Exit from Menu)"),
        Line::from("  ? / h            Toggle this help overlay"),
        Line::from("  q / Ctrl+C       Exit cleanly to Linux shell"),
    ];
    let help = Paragraph::new(lines)
        .wrap(Wrap { trim: false })
        .block(
            Block::default()
                .title(" Help (Esc to close) ")
                .borders(Borders::ALL)
                .border_style(theme.border_style(true)),
        );
    frame.render_widget(help, rect);
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::modules::default_modules;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    #[test]
    fn renders_responsively_across_terminal_sizes() {
        let modules = default_modules();
        let state = AppState::new(modules.len());
        let theme = Theme::default();

        for (w, h) in [(80, 24), (50, 20), (35, 15)] {
            let backend = TestBackend::new(w, h);
            let mut terminal = Terminal::new(backend).unwrap();
            terminal
                .draw(|f| render(f, &state, &modules, &theme))
                .unwrap();
        }
    }
}
