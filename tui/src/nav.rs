use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

use crate::events::AppEvent;
use crate::modules::PageModule;
use crate::state::{AppState, Focus};

pub fn handle_event(state: &mut AppState, modules: &mut [Box<dyn PageModule>], event: AppEvent) {
    match event {
        AppEvent::Resize(w, h) => {
            state.status_hint = format!("Resized to {}x{}", w, h);
        }
        AppEvent::Key(key) => handle_key(state, modules, key),
    }
}

pub fn handle_key(state: &mut AppState, modules: &mut [Box<dyn PageModule>], key: KeyEvent) {
    // Ctrl+C always exits cleanly to the shell.
    if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
        state.should_quit = true;
        return;
    }

    // Help overlay captures Esc/?/h/q.
    if state.show_help {
        match key.code {
            KeyCode::Esc | KeyCode::Char('?') | KeyCode::Char('h') | KeyCode::Enter => {
                state.show_help = false;
            }
            KeyCode::Char('q') => state.should_quit = true,
            _ => {}
        }
        return;
    }

    match key.code {
        KeyCode::Char('q') => {
            state.should_quit = true;
            return;
        }
        KeyCode::Char('?') | KeyCode::Char('h') => {
            state.show_help = true;
            return;
        }
        KeyCode::Tab => {
            state.toggle_focus();
            state.status_hint = match state.focus {
                Focus::Menu => "Focus: Menu".to_string(),
                Focus::Content => "Focus: Page".to_string(),
            };
            return;
        }
        KeyCode::BackTab => {
            state.toggle_focus();
            state.status_hint = match state.focus {
                Focus::Menu => "Focus: Menu".to_string(),
                Focus::Content => "Focus: Page".to_string(),
            };
            return;
        }
        _ => {}
    }

    match state.focus {
        Focus::Menu => match key.code {
            KeyCode::Up | KeyCode::Char('k') => {
                state.select_prev();
                state.status_hint = format!("Selected: {}", current_title(state, modules));
            }
            KeyCode::Down | KeyCode::Char('j') => {
                state.select_next();
                state.status_hint = format!("Selected: {}", current_title(state, modules));
            }
            KeyCode::Enter | KeyCode::Right => {
                state.focus = Focus::Content;
                state.status_hint = format!("Opened: {}", current_title(state, modules));
            }
            KeyCode::Esc => {
                state.should_quit = true;
            }
            _ => {}
        },
        Focus::Content => match key.code {
            KeyCode::Esc | KeyCode::Left => {
                state.focus = Focus::Menu;
                state.status_hint = "Returned to menu".to_string();
            }
            _ => {
                if let Some(module) = modules.get_mut(state.selected_index) {
                    if let Some(msg) = module.handle_key(key) {
                        state.status_hint = msg;
                    }
                }
            }
        },
    }
}

fn current_title<'a>(state: &AppState, modules: &'a [Box<dyn PageModule>]) -> &'a str {
    modules
        .get(state.selected_index)
        .map(|m| m.title())
        .unwrap_or("None")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::modules::default_modules;

    fn key(code: KeyCode) -> KeyEvent {
        KeyEvent::new(code, KeyModifiers::NONE)
    }

    #[test]
    fn navigation_and_escape_flow() {
        let mut modules = default_modules();
        let mut state = AppState::new(modules.len());

        assert_eq!(state.selected_index, 0);
        assert_eq!(state.focus, Focus::Menu);

        handle_key(&mut state, &mut modules, key(KeyCode::Down));
        assert_eq!(state.selected_index, 1);

        handle_key(&mut state, &mut modules, key(KeyCode::Enter));
        assert_eq!(state.focus, Focus::Content);

        // Esc in content returns to menu instead of quitting.
        handle_key(&mut state, &mut modules, key(KeyCode::Esc));
        assert_eq!(state.focus, Focus::Menu);
        assert!(!state.should_quit);

        // Esc in menu exits cleanly.
        handle_key(&mut state, &mut modules, key(KeyCode::Esc));
        assert!(state.should_quit);
    }

    #[test]
    fn tab_and_ctrl_c_behave_cleanly() {
        let mut modules = default_modules();
        let mut state = AppState::new(modules.len());

        handle_key(&mut state, &mut modules, key(KeyCode::Tab));
        assert_eq!(state.focus, Focus::Content);

        handle_key(&mut state, &mut modules, key(KeyCode::BackTab));
        assert_eq!(state.focus, Focus::Menu);

        handle_key(
            &mut state,
            &mut modules,
            KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL),
        );
        assert!(state.should_quit);
    }
}
