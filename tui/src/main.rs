mod events;
mod modules;
mod nav;
mod state;
mod terminal;
mod theme;
mod ui;

use std::io;
use std::path::PathBuf;

use crate::events::next_event;
use crate::modules::default_modules;
use crate::nav::handle_event;
use crate::state::AppState;
use crate::terminal::TerminalGuard;
use crate::theme::Theme;

fn parse_theme_arg() -> Option<PathBuf> {
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--theme" => return args.next().map(PathBuf::from),
            "--version" | "-V" => {
                println!("naomi-tui {}", env!("CARGO_PKG_VERSION"));
                std::process::exit(0);
            }
            "--help" | "-h" => {
                println!("Usage: naomi-tui [--theme <path>] [--version]");
                std::process::exit(0);
            }
            _ => {}
        }
    }
    None
}

fn main() -> io::Result<()> {
    let theme_path = parse_theme_arg();
    let theme = Theme::load(theme_path.as_deref());
    let mut modules = default_modules();
    let mut state = AppState::new(modules.len());

    let mut term = TerminalGuard::enter()?;

    loop {
        term.terminal().draw(|frame| {
            ui::render(frame, &state, &modules, &theme);
        })?;

        if state.should_quit {
            break;
        }

        // Pure event-driven blocking read: 0% idle CPU.
        if let Some(ev) = next_event()? {
            handle_event(&mut state, &mut modules, ev);
            if state.should_quit {
                break;
            }
        }
    }

    Ok(())
}
