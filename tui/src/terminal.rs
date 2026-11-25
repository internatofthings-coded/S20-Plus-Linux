use std::io::{self, Stdout};
use std::panic;

use crossterm::execute;
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use ratatui::backend::CrosstermBackend;
use ratatui::Terminal;

pub type AppTerminal = Terminal<CrosstermBackend<Stdout>>;

/// RAII guard that guarantees terminal restoration on normal exit, error, or panic.
pub struct TerminalGuard {
    terminal: AppTerminal,
}

impl TerminalGuard {
    pub fn enter() -> io::Result<Self> {
        install_panic_hook();
        enable_raw_mode()?;
        let mut stdout = io::stdout();
        if let Err(err) = execute!(stdout, EnterAlternateScreen) {
            let _ = disable_raw_mode();
            return Err(err);
        }
        let backend = CrosstermBackend::new(stdout);
        let mut terminal = match Terminal::new(backend) {
            Ok(t) => t,
            Err(err) => {
                let _ = restore_raw_terminal();
                return Err(err);
            }
        };
        terminal.clear()?;
        Ok(Self { terminal })
    }

    pub fn terminal(&mut self) -> &mut AppTerminal {
        &mut self.terminal
    }
}

impl Drop for TerminalGuard {
    fn drop(&mut self) {
        let _ = restore_raw_terminal();
        let _ = self.terminal.show_cursor();
    }
}

pub fn restore_raw_terminal() -> io::Result<()> {
    let _ = disable_raw_mode();
    let mut stdout = io::stdout();
    execute!(stdout, LeaveAlternateScreen, crossterm::cursor::Show)
}

fn install_panic_hook() {
    let prev = panic::take_hook();
    panic::set_hook(Box::new(move |info| {
        let _ = restore_raw_terminal();
        prev(info);
    }));
}
