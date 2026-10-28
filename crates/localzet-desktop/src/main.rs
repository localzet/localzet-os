//! Localzet Desktop control center and application launcher.
use gtk::prelude::*;
use gtk::{
    Application, ApplicationWindow, Box as GtkBox, Button, Label, Orientation, ScrolledWindow,
    TextView,
};
use std::ffi::OsStr;
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

fn scan_storage(output: TextView) {
    let argv = [
        OsStr::new("python3"),
        OsStr::new("/opt/localzet-os/scripts/installer-preflight.py"),
    ];
    let process = match gtk::gio::Subprocess::newv(
        &argv,
        gtk::gio::SubprocessFlags::STDOUT_PIPE | gtk::gio::SubprocessFlags::STDERR_PIPE,
    ) {
        Ok(process) => process,
        Err(error) => {
            output
                .buffer()
                .set_text(&format!("Не удалось начать проверку: {error}"));
            return;
        }
    };
    output.buffer().set_text("Читаю сведения о накопителях…");
    gtk::glib::spawn_future_local(async move {
        let message = match process.communicate_utf8_future(None).await {
            Ok((stdout, _stderr)) if process.exit_status() == 0 => {
                stdout.map(|text| text.to_string()).unwrap_or_default()
            }
            Ok((_, stderr)) => format!(
                "Проверка не завершилась.\n{}",
                stderr.map(|text| text.to_string()).unwrap_or_default()
            ),
            Err(error) => format!("Не удалось получить результат проверки: {error}"),
        };
        output.buffer().set_text(&message);
    });
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
        let install_heading = Label::new(Some("Установка Localzet OS · предварительная проверка"));
        install_heading.add_css_class("title-1");
        install_heading.set_halign(gtk::Align::Start);
        root.append(&install_heading);
        let install_note = Label::new(Some(
            "Установщик ещё не готов. Сканирование только читает сведения о дисках и ничего не записывает.",
        ));
        install_note.set_wrap(true);
        install_note.set_halign(gtk::Align::Start);
        root.append(&install_note);
        let inventory = TextView::new();
        inventory.set_editable(false);
        inventory.set_cursor_visible(false);
        inventory.set_monospace(true);
        inventory.buffer().set_text("Проверка только читает сведения о дисках. Обнаружение ОС доступно в отдельном контексте установщика.");
        let scan = Button::with_label("Проверить диски и установленные ОС (без записи)");
        let inventory_copy = inventory.clone();
        scan.connect_clicked(move |_| scan_storage(inventory_copy.clone()));
        root.append(&scan);
        let inventory_scroll = ScrolledWindow::new();
        inventory_scroll.set_min_content_height(180);
        inventory_scroll.set_child(Some(&inventory));
        root.append(&inventory_scroll);
        let note = Label::new(Some("Experimental live session. Disk installation is not supported. Updates and other changes are lost after reboot."));
        note.set_wrap(true);
        note.set_halign(gtk::Align::Start);
        root.append(&note);
        window.set_child(Some(&root));
        window.present();
    });
    app.run();
}
