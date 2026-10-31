//! Compact Localzet Surface shell for 1080p desktops.
//! True background blur needs compositor support; these surfaces use alpha only.
use gtk::prelude::*;
use gtk::{
    Application, ApplicationWindow, Box as GtkBox, Button, CenterBox, Image, Label, Orientation,
};
use gtk4_layer_shell::{Edge, Layer, LayerShell};
use std::process::Command;

const CSS: &str = r#"* { font-family: "Noto Sans", sans-serif; }
window { background: transparent; }
.surface-bar, .surface-dock {
 background: rgba(23, 19, 47, 0.79); color: #f6f2ff;
 border: 1px solid rgba(211,192,255,0.30);
 box-shadow: 0 10px 30px rgba(12,8,33,0.38);
}
.surface-bar { min-height: 36px; padding: 0 14px; border-radius: 0 0 14px 14px; border-top: 0; }
.surface-dock { padding: 7px 11px; border-radius: 21px; }
.surface-bar button, .surface-dock button { background: transparent; border: 0; color: #f0eaff; border-radius: 12px; padding: 0; box-shadow: none; }
.surface-bar button { min-width: 32px; min-height: 30px; }
.surface-bar button image { -gtk-icon-size: 15px; }
.surface-dock button { min-width: 45px; min-height: 45px; }
.surface-dock button image { -gtk-icon-size: 26px; }
.surface-bar button:hover, .surface-dock button:hover { background: rgba(192,160,255,0.24); }
.surface-dock .start-button { background: rgba(142,105,250,0.30); }
.surface-bar .clock { font-size: 12px; font-weight: 600; color: #f7edff; }"#;

fn launch(program: &'static str) {
    if let Err(error) = Command::new(program).spawn() {
        eprintln!("Failed to launch {program}: {error}");
    }
}

fn icon_button(icon: &str, tooltip: &str, program: &'static str) -> Button {
    let button = Button::new();
    button.set_child(Some(&Image::from_icon_name(icon)));
    button.set_tooltip_text(Some(tooltip));
    button.connect_clicked(move |_| launch(program));
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
    let window = ApplicationWindow::builder()
        .application(app)
        .title("Localzet Top Bar")
        .build();
    window.init_layer_shell();
    window.set_namespace("localzet-top-bar");
    window.set_layer(Layer::Top);
    for edge in [Edge::Top, Edge::Left, Edge::Right] {
        window.set_anchor(edge, true);
    }
    window.set_exclusive_zone(40);

    let layout = CenterBox::new();
    layout.add_css_class("surface-bar");
    let left = GtkBox::new(Orientation::Horizontal, 4);
    let start = icon_button("view-app-grid-symbolic", "Приложения", "localzet-launcher");
    start.add_css_class("brand-button");
    left.append(&start);
    layout.set_start_widget(Some(&left));

    let clock = Label::new(Some(&clock_text()));
    clock.add_css_class("clock");
    layout.set_center_widget(Some(&clock));
    gtk::glib::timeout_add_seconds_local(15, move || {
        clock.set_text(&clock_text());
        gtk::glib::ControlFlow::Continue
    });

    let right = GtkBox::new(Orientation::Horizontal, 4);
    right.append(&icon_button(
        "audio-volume-high-symbolic",
        "Звук",
        "pavucontrol",
    ));
    right.append(&icon_button(
        "network-wireless-symbolic",
        "Сетевые подключения",
        "nm-connection-editor",
    ));
    layout.set_end_widget(Some(&right));
    window.set_child(Some(&layout));
    window.present();
}

fn dock(app: &Application) {
    let window = ApplicationWindow::builder()
        .application(app)
        .title("Localzet Dock")
        .build();
    window.init_layer_shell();
    window.set_namespace("localzet-dock");
    window.set_layer(Layer::Top);
    window.set_anchor(Edge::Bottom, true);
    window.set_margin(Edge::Bottom, 10);
    window.set_exclusive_zone(0);

    let bar = GtkBox::new(Orientation::Horizontal, 3);
    bar.add_css_class("surface-dock");
    let start = icon_button("view-app-grid-symbolic", "Пуск", "localzet-launcher");
    start.add_css_class("start-button");
    bar.append(&start);
    bar.append(&icon_button("org.gnome.Nautilus", "Файлы", "nautilus"));
    bar.append(&icon_button("org.gnome.Ptyxis", "Терминал", "ptyxis"));
    bar.append(&icon_button(
        "network-wireless-symbolic",
        "Настройки сети",
        "nm-connection-editor",
    ));
    window.set_child(Some(&bar));
    window.present();
}

fn main() {
    let app = Application::builder()
        .application_id("cloud.localzet.Panel")
        .build();
    app.connect_activate(|app| {
        let provider = gtk::CssProvider::new();
        provider.load_from_data(CSS);
        if let Some(display) = gtk::gdk::Display::default() {
            gtk::style_context_add_provider_for_display(
                &display,
                &provider,
                gtk::STYLE_PROVIDER_PRIORITY_APPLICATION,
            );
        }
        top_bar(app);
        dock(app);
    });
    app.run();
}
