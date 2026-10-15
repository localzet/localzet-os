//! Localzet Desktop control center and application launcher.
use gtk::prelude::*;
use gtk::{
    Application, ApplicationWindow, Box as GtkBox, Button, Label, Orientation, ScrolledWindow,
};
use std::process::Command;

const STYLE: &str = r#"
window { background: #19162d; color: #f3edff; }
button { background: rgba(126, 91, 202, 0.25); color: #f5edff;
 border: 1px solid rgba(211, 185, 255, 0.25); border-radius: 12px;
 padding: 9px 14px; }
button:hover { background: rgba(168, 122, 246, 0.38); }
label.title-1 { color: #f8edff; }
"#;

fn command_button(label: &str, executable: &'static str, args: &'static [&'static str]) -> Button {
    let button = Button::with_label(label);
    button.connect_clicked(move |_| {
        if let Err(error) = Command::new(executable).args(args).spawn() {
            eprintln!("Cannot start {executable}: {error}");
        }
    });
    button
}

fn main() {
    let app = Application::builder()
        .application_id("cloud.localzet.Desktop")
        .build();
    app.connect_activate(|app| {
        let window = ApplicationWindow::builder()
            .application(app)
            .title("Localzet Desktop")
            .default_width(960)
            .default_height(680)
            .build();
        let provider = gtk::CssProvider::new();
        provider.load_from_data(STYLE);
        if let Some(display) = gtk::gdk::Display::default() {
            gtk::style_context_add_provider_for_display(
                &display,
                &provider,
                gtk::STYLE_PROVIDER_PRIORITY_APPLICATION,
            );
        }
        let root = GtkBox::new(Orientation::Vertical, 18);
        root.set_margin_top(30);
        root.set_margin_bottom(30);
        root.set_margin_start(36);
        root.set_margin_end(36);
        let heading = Label::new(Some("Localzet OS"));
        heading.add_css_class("title-1");
        heading.set_halign(gtk::Align::Start);
        root.append(&heading);
        let subtitle = Label::new(Some("Desktop · Applications · System"));
        subtitle.set_halign(gtk::Align::Start);
        root.append(&subtitle);
        let actions = GtkBox::new(Orientation::Horizontal, 10);
        for (name, executable, args) in [
            ("Applications", "localzet-launcher", &[][..]),
            ("Terminal", "foot", &[][..]),
            ("Files", "thunar", &[][..]),
            ("Network", "nm-connection-editor", &[][..]),
            ("Audio", "pavucontrol", &[][..]),
        ] {
            actions.append(&command_button(name, executable, args));
        }
        root.append(&actions);
        let status = Label::new(Some("Select Check system to inspect the Localzet service."));
        status.set_selectable(true);
        status.set_wrap(true);
        status.set_halign(gtk::Align::Start);
        let check = Button::with_label("Check system");
        let status_copy = status.clone();
        check.connect_clicked(move |_| {
            let output = Command::new("localzetctl").arg("status").output();
            let message = match output {
                Ok(result) if result.status.success() => String::from_utf8_lossy(&result.stdout).trim().to_owned(),
                Ok(result) => format!("Service unavailable: {}", String::from_utf8_lossy(&result.stderr).trim()),
                Err(error) => format!("localzetctl unavailable: {error}"),
            };
            status_copy.set_text(&message);
        });
        root.append(&check);
        let scroll = ScrolledWindow::new();
        scroll.set_vexpand(true);
        scroll.set_child(Some(&status));
        root.append(&scroll);
        let note = Label::new(Some("Experimental live session. Disk installation is not supported. GNOME and Linux apps remain available through the Debian base."));
        note.set_wrap(true);
        note.set_halign(gtk::Align::Start);
        root.append(&note);
        window.set_child(Some(&root));
        window.present();
    });
    app.run();
}
