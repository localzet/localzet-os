//! Localzet Surface: top status bar and floating application dock.
//! GTK layer-shell supplies the surfaces; blur requires compositor support.
use gtk::prelude::*;
use gtk::{Application, ApplicationWindow, Box as GtkBox, Button, CenterBox, Label, Orientation};
use gtk4_layer_shell::{Edge, Layer, LayerShell};
use std::process::Command;

const CSS: &str = r#"
* { font-family: 'Noto Sans', sans-serif; }
window { background: transparent; }
.surface-bar, .surface-dock {
  background: rgba(18, 24, 37, 0.82);
  color: #f2f5fc;
  border: 1px solid rgba(225, 235, 255, 0.17);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.30);
}
.surface-bar { border-radius: 16px; padding: 4px 14px; }
.surface-dock { border-radius: 23px; padding: 7px 9px; }
.surface-bar button, .surface-dock button {
  background: transparent; color: #e8efff;
  border: 0; border-radius: 14px; min-height: 34px;
  padding: 4px 13px; font-weight: 600;
}
.surface-dock button { min-height: 45px; min-width: 48px; font-size: 19px; }
.surface-bar button:hover, .surface-dock button:hover {
  background: rgba(255, 255, 255, 0.14);
}
.surface-dock .start-button {
  background: rgba(98, 150, 255, 0.23);
  color: #c6d9ff;
}
.surface-bar .clock { color: #f6f8ff; font-weight: 700; font-size: 13px; }
.surface-bar .status { color: #cbd6e9; font-size: 12px; }
"#;

fn run(program: &'static str, args: &'static [&'static str]) {
    if let Err(error) = Command::new(program).args(args).spawn() {
        eprintln!("Could not launch {program}: {error}");
    }
}

fn action(label: &str, tooltip: &str, program: &'static str, args: &'static [&'static str]) -> Button {
    let button = Button::with_label(label);
    button.set_tooltip_text(Some(tooltip));
    button.connect_clicked(move |_| run(program, args));
    button
}

fn clock_text() -> String {
    gtk::glib::DateTime::now_local()
        .ok()
        .and_then(|now| now.format("%a, %d %b  %H:%M").ok())
        .map(|value| value.to_string())
        .unwrap_or_else(|| "--:--".to_string())
}

fn top_bar(app: &Application) {
    let window = ApplicationWindow::builder().application(app).title("Localzet Top Bar").build();
    window.init_layer_shell();
    window.set_namespace("localzet-top-bar");
    window.set_layer(Layer::Top);
    window.set_anchor(Edge::Top, true);
    window.set_anchor(Edge::Left, true);
    window.set_anchor(Edge::Right, true);
    window.set_margin(Edge::Top, 8);
    window.set_margin(Edge::Left, 12);
    window.set_margin(Edge::Right, 12);
    window.set_exclusive_zone(54);

    let layout = CenterBox::new();
    layout.add_css_class("surface-bar");
    let left = GtkBox::new(Orientation::Horizontal, 6);
    left.append(&action("◈ Localzet", "Applications", "localzet-launcher", &[]));
    layout.set_start_widget(Some(&left));

    let clock = Label::new(Some(&clock_text()));
    clock.add_css_class("clock");
    layout.set_center_widget(Some(&clock));
    gtk::glib::timeout_add_seconds_local(15, move || {
        clock.set_text(&clock_text());
        gtk::glib::ControlFlow::Continue
    });

    let right = GtkBox::new(Orientation::Horizontal, 8);
    let status = Label::new(Some("●  Localzet OS"));
    status.add_css_class("status");
    right.append(&status);
    right.append(&action("⚙", "Sound settings", "pavucontrol", &[]));
    layout.set_end_widget(Some(&right));
    window.set_child(Some(&layout));
    window.present();
}

fn dock(app: &Application) {
    let window = ApplicationWindow::builder().application(app).title("Localzet Dock").build();
    window.init_layer_shell();
    window.set_namespace("localzet-dock");
    window.set_layer(Layer::Top);
    window.set_anchor(Edge::Bottom, true);
    window.set_margin(Edge::Bottom, 16);
    // Floating dock: don't reserve the entire bottom edge.
    window.set_exclusive_zone(0);

    let bar = GtkBox::new(Orientation::Horizontal, 5);
    bar.add_css_class("surface-dock");
    let start = action("◈", "Start · applications", "localzet-launcher", &[]);
    start.add_css_class("start-button");
    bar.append(&start);
    bar.append(&action("⌘", "Terminal", "foot", &[]));
    bar.append(&action("▣", "Files", "thunar", &[]));
    bar.append(&action("◉", "Localzet Desktop", "localzet-desktop", &[]));
    window.set_child(Some(&bar));
    window.present();
}

fn main() {
    let app = Application::builder().application_id("cloud.localzet.Panel").build();
    app.connect_activate(|app| {
        let provider = gtk::CssProvider::new();
        provider.load_from_data(CSS);
        if let Some(display) = gtk::gdk::Display::default() {
            gtk::style_context_add_provider_for_display(
                &display, &provider, gtk::STYLE_PROVIDER_PRIORITY_APPLICATION,
            );
        }
        top_bar(app);
        dock(app);
    });
    app.run();
}
