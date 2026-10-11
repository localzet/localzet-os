//! Searchable application launcher. Uses GIO desktop entries, not shell commands.
use gtk::prelude::*;
use gtk::{gio, Application, ApplicationWindow, Box as GtkBox, Entry, Label, ListBox, ListBoxRow, Orientation, ScrolledWindow};
use gtk4_layer_shell::{Edge, KeyboardMode, Layer, LayerShell};

fn fill(list: &ListBox, query: &str, window: &ApplicationWindow) {
    while let Some(child) = list.first_child() { list.remove(&child); }
    let needle = query.to_lowercase();
    let mut apps = gio::AppInfo::all();
    apps.sort_by_key(|app| app.display_name().to_lowercase());
    for app in apps.into_iter().filter(|a| a.should_show()) {
        let name = app.display_name().to_string();
        if !name.to_lowercase().contains(&needle) { continue; }
        let row = ListBoxRow::new();
        row.set_child(Some(&Label::builder().label(&name).xalign(0.0).margin_top(8).margin_bottom(8).margin_start(12).build()));
        let app_copy = app.clone();
        let window_copy = window.clone();
        row.connect_activate(move |_| {
            let context = gio::AppLaunchContext::new();
            if let Err(error) = app_copy.launch(&[], Some(&context)) {
                eprintln!("Could not launch application: {error}");
            } else {
                window_copy.close();
            }
        });
        list.append(&row);
    }
}

fn main() {
    let app = Application::builder().application_id("cloud.localzet.Launcher").build();
    app.connect_activate(|app| {
        let window = ApplicationWindow::builder().application(app).title("Applications").default_width(550).default_height(600).build();
        window.init_layer_shell();
        window.set_layer(Layer::Overlay);
        window.set_anchor(Edge::Top, true);
        window.set_margin(Edge::Top, 64);
        window.set_keyboard_mode(KeyboardMode::Exclusive);
        window.set_namespace("localzet-launcher");
        let root = GtkBox::new(Orientation::Vertical, 10);
        root.set_margin_start(14); root.set_margin_end(14);
        root.set_margin_top(14); root.set_margin_bottom(14);
        let search = Entry::builder().placeholder_text("Search applications…").build();
        let list = ListBox::new();
        list.set_activate_on_single_click(true);
        let scroll = ScrolledWindow::builder().vexpand(true).child(&list).build();
        root.append(&search); root.append(&scroll);
        window.set_child(Some(&root));
        fill(&list, "", &window);
        let list_copy = list.clone();
        let window_copy = window.clone();
        search.connect_changed(move |entry| fill(&list_copy, entry.text().as_str(), &window_copy));
        let key = gtk::EventControllerKey::new();
        let close_window = window.clone();
        key.connect_key_pressed(move |_, key, _, _| {
            if key == gtk::gdk::Key::Escape { close_window.close(); return gtk::glib::Propagation::Stop; }
            gtk::glib::Propagation::Proceed
        });
        window.add_controller(key);
        window.present();
        search.grab_focus();
    });
    app.run();
}
