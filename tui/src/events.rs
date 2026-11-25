use std::io;

use crossterm::event::{self, Event, KeyEvent, KeyEventKind};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AppEvent {
    Key(KeyEvent),
    Resize(u16, u16),
}

/// Blocking event read: sleeps in kernel poll/read until input or SIGWINCH arrives.
pub fn next_event() -> io::Result<Option<AppEvent>> {
    match event::read()? {
        Event::Key(key) if key.kind == KeyEventKind::Press => Ok(Some(AppEvent::Key(key))),
        Event::Resize(w, h) => Ok(Some(AppEvent::Resize(w, h))),
        _ => Ok(None),
    }
}
