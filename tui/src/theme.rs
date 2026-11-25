use std::env;
use std::fs;
use std::path::Path;

use ratatui::style::{Color, Modifier, Style};

const DEFAULT_THEME_PATH: &str = "/etc/boros/tui-theme.conf";

#[derive(Debug, Clone)]
pub struct Theme {
    pub header_title: String,
    pub accent: Color,
    pub highlight_bg: Color,
    pub highlight_fg: Color,
    pub border: Color,
    pub text: Color,
    pub muted: Color,
    pub menu_width: u16,
    pub monochrome: bool,
}

impl Default for Theme {
    fn default() -> Self {
        Self {
            header_title: "NAOMI".to_string(),
            accent: Color::Red,
            highlight_bg: Color::DarkGray,
            highlight_fg: Color::White,
            border: Color::Gray,
            text: Color::Reset,
            muted: Color::DarkGray,
            menu_width: 20,
            monochrome: false,
        }
    }
}

impl Theme {
    pub fn load(override_path: Option<&Path>) -> Self {
        let mut theme = Self::default();
        let path = override_path.unwrap_or_else(|| Path::new(DEFAULT_THEME_PATH));
        if let Ok(content) = fs::read_to_string(path) {
            theme.apply_config(&content);
        }
        if is_monochrome_env() {
            theme.apply_monochrome();
        }
        theme
    }

    pub fn apply_config(&mut self, content: &str) {
        for raw_line in content.lines() {
            let line = raw_line.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            let Some((k, v)) = line.split_once('=') else {
                continue;
            };
            let key = k.trim();
            let val = v.trim();
            match key {
                "header_title" if !val.is_empty() => self.header_title = val.to_string(),
                "accent" => {
                    if let Some(c) = parse_color(val) {
                        self.accent = c;
                    }
                }
                "highlight_bg" => {
                    if let Some(c) = parse_color(val) {
                        self.highlight_bg = c;
                    }
                }
                "highlight_fg" => {
                    if let Some(c) = parse_color(val) {
                        self.highlight_fg = c;
                    }
                }
                "border" => {
                    if let Some(c) = parse_color(val) {
                        self.border = c;
                    }
                }
                "text" => {
                    if let Some(c) = parse_color(val) {
                        self.text = c;
                    }
                }
                "muted" => {
                    if let Some(c) = parse_color(val) {
                        self.muted = c;
                    }
                }
                "menu_width" => {
                    if let Ok(w) = val.parse::<u16>() {
                        self.menu_width = w.clamp(12, 36);
                    }
                }
                _ => {}
            }
        }
    }

    pub fn apply_monochrome(&mut self) {
        self.monochrome = true;
        self.accent = Color::Reset;
        self.highlight_bg = Color::Reset;
        self.highlight_fg = Color::Reset;
        self.border = Color::Reset;
        self.text = Color::Reset;
        self.muted = Color::Reset;
    }

    pub fn header_style(&self) -> Style {
        if self.monochrome {
            Style::default().add_modifier(Modifier::BOLD)
        } else {
            Style::default().fg(self.accent).add_modifier(Modifier::BOLD)
        }
    }

    pub fn selected_style(&self) -> Style {
        if self.monochrome {
            Style::default().add_modifier(Modifier::REVERSED | Modifier::BOLD)
        } else {
            Style::default()
                .fg(self.highlight_fg)
                .bg(self.highlight_bg)
                .add_modifier(Modifier::BOLD)
        }
    }

    pub fn border_style(&self, focused: bool) -> Style {
        if self.monochrome {
            if focused {
                Style::default().add_modifier(Modifier::BOLD)
            } else {
                Style::default()
            }
        } else if focused {
            Style::default().fg(self.accent)
        } else {
            Style::default().fg(self.border)
        }
    }

    pub fn muted_style(&self) -> Style {
        if self.monochrome {
            Style::default().add_modifier(Modifier::DIM)
        } else {
            Style::default().fg(self.muted)
        }
    }
}

fn is_monochrome_env() -> bool {
    if env::var_os("NO_COLOR").is_some() {
        return true;
    }
    matches!(env::var("TERM").as_deref(), Ok("dumb") | Ok("vt100"))
}

fn parse_color(s: &str) -> Option<Color> {
    if let Some(hex) = s.strip_prefix('#') {
        if hex.len() == 6 {
            let r = u8::from_str_radix(&hex[0..2], 16).ok()?;
            let g = u8::from_str_radix(&hex[2..4], 16).ok()?;
            let b = u8::from_str_radix(&hex[4..6], 16).ok()?;
            return Some(Color::Rgb(r, g, b));
        }
        return None;
    }
    match s.to_ascii_lowercase().as_str() {
        "black" => Some(Color::Black),
        "red" => Some(Color::Red),
        "green" => Some(Color::Green),
        "yellow" => Some(Color::Yellow),
        "blue" => Some(Color::Blue),
        "magenta" => Some(Color::Magenta),
        "cyan" => Some(Color::Cyan),
        "gray" | "grey" => Some(Color::Gray),
        "dark_gray" | "dark_grey" => Some(Color::DarkGray),
        "light_red" => Some(Color::LightRed),
        "light_green" => Some(Color::LightGreen),
        "light_yellow" => Some(Color::LightYellow),
        "light_blue" => Some(Color::LightBlue),
        "light_magenta" => Some(Color::LightMagenta),
        "light_cyan" => Some(Color::LightCyan),
        "white" => Some(Color::White),
        "reset" => Some(Color::Reset),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_config_and_clamps_width() {
        let mut t = Theme::default();
        t.apply_config("header_title = CUSTOM\naccent = #ff0000\nmenu_width = 99\n");
        assert_eq!(t.header_title, "CUSTOM");
        assert_eq!(t.accent, Color::Rgb(255, 0, 0));
        assert_eq!(t.menu_width, 36);
    }

    #[test]
    fn monochrome_clears_colors() {
        let mut t = Theme::default();
        t.apply_monochrome();
        assert!(t.monochrome);
        assert_eq!(t.accent, Color::Reset);
    }
}
