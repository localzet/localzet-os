//! Localzet's first native Wayland panel. labwc still owns window management.
use gtk::prelude::*;
use gtk::{Application, ApplicationWindow, Box as GtkBox, Button, Label, Orientation};
use gtk4_layer_shell::{Edge, Layer, LayerShell};
use std::process::Command;

fn launch(command: &'static str, args: &'static [&'static str]) -> Button {
    let button = Button::with_label(command);
    button.connect_clicked(move |_| {
        if let Err(error) = Command::new(command).args(args).spawn() {
            eprintln!("Unable to start {command}: {error}");
        }
    });
    button
}

fn main() {
    let app = Application::builder().application_id("cloud.localzet.Panel").build();
    app.connect_activate(|app| {
        let window = ApplicationWindow::builder()
            .application(app).title("Localzet Panel").build();
        window.init_layer_shell();
        window.set_layer(Layer::Top);
        window.set_anchor(Edge::Top, true);
        window.set_anchor(Edge::Left, true);
        window.set_anchor(Edge::Right, true);
        window.auto_exclusive_zone_enable();
        window.set_namespace(Some("localzet-panel"));
        let bar = GtkBox::new(Orientation::Horizontal, 12);
        bar.set_margin_start(14);
        bar.set_margin_end(14);
        bar.set_margin_top(6);
        bar.set_margin_bottom(6);
        bar.add_css_class("localzet-panel");
        let menu = Button::with_label("◈ Localzet");
        menu.connect_clicked(|_| {
            if let Err(error) = Command::new("localzet-launcher").spawn() {
                eprintln!("Unable to open launcher: {error}");
            }
        });
        bar.append(&menu);
        bar.append(&launch("foot", &[]));
        bar.append(&launch("thunar", &[]));
        bar.append(&launch("localzet-desktop", &[]));
        let spacer = GtkBox::new(Orientation::Horizontal, 0);
        spacer.set_hexpand(true);
        bar.append(&spacer);
        let clock = Label::new(None);
        clock.add_css_class("clock");
        bar.append(&clock);
        let refresh = clock.clone();
        gtk::glib::timeout_add_seconds_local(1, move || {
            if let Ok(now) = gtk::glib::DateTime::now_local() {
                if let Ok(display) = now.format("%a %d %b  %H:%M") {
                    refresh.set_text(&display);
                }
            }
            gtk::glib::ControlFlow::Continue
        });
        let provider = gtk::CssProvider::new();
        provider.load_from_data(".localzet-panel { background: #172333; border-bottom: 1px solid #38506b; } .localzet-panel button { background: #253950; color: #eef5ff; border-radius: 8px; } .localzet-panel .clock { color: #eef5ff; font-weight: bold; }");
        gtk::style_context_add_provider_for_display(
            &gtk::gdk::Display::default().expect("Wayland display required"),
            &provider, gtk::STYLE_PROVIDER_PRIORITY_APPLICATION,
        );
        window.set_child(Some(&bar));
        window.present();
    });
    app.run();
}
