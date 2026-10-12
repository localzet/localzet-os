//! Localzet Surface launcher: compact searchable application grid.
//! Application launch uses GIO desktop entries, never interpolated shell commands.
use gtk::prelude::*;
use gtk::{gio, glib, Application, ApplicationWindow, Box as GtkBox, Button, Entry, FlowBox, Image, Label, Orientation, ScrolledWindow};
use gtk4_layer_shell::{Edge, KeyboardMode, Layer, LayerShell};
use std::{cell::Cell, rc::Rc, collections::HashSet, fs, path::PathBuf};

fn favorites_path() -> Option<PathBuf> {
    let base = std::env::var_os("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("HOME").map(|home| PathBuf::from(home).join(".config")))?;
    Some(base.join("localzet-os").join("favorites"))
}

fn load_favorites() -> HashSet<String> {
    favorites_path().and_then(|path| fs::read_to_string(path).ok())
        .map(|text| text.lines().map(str::trim).filter(|id| !id.is_empty()).map(str::to_owned).collect())
        .unwrap_or_default()
}

fn save_favorites(favorites: &HashSet<String>) -> std::io::Result<()> {
    let path = favorites_path().ok_or_else(|| std::io::Error::other("HOME and XDG_CONFIG_HOME are unset"))?;
    if let Some(parent) = path.parent() { fs::create_dir_all(parent)?; }
    let mut ids: Vec<_> = favorites.iter().collect();
    ids.sort();
    fs::write(path, ids.into_iter().map(|id| id.as_str()).collect::<Vec<_>>().join("\\n") + "\\n")
}


const STYLE: &str = r#"
* { font-family: 'Noto Sans', sans-serif; }
window { background: transparent; }
.launcher {
 background: rgba(17, 23, 38, 0.96); color: #eef3ff;
 border: 1px solid rgba(190, 210, 255, 0.22);
 border-radius: 20px; padding: 14px;
 box-shadow: 0 18px 50px rgba(0,0,0,0.35);
}
.launcher entry {
 background: rgba(255,255,255,0.08); color: #ffffff;
 border: 1px solid rgba(220,230,255,0.12);
 border-radius: 11px; min-height: 32px; padding: 4px 10px;
}
.launcher .heading { font-size: 12px; font-weight: 700; color: #aabbdc; }
.launcher .hint { font-size: 10px; color: #8191af; }
.launcher flowbox, .launcher flowboxchild { background: transparent; }
.launcher flowboxchild { border-radius: 12px; }
.launcher flowboxchild:hover, .launcher flowboxchild:selected {
 background: rgba(126,165,255,0.17);
}
.app-tile { min-width: 92px; min-height: 78px; padding: 8px 3px; }
.app-tile image { -gtk-icon-size: 30px; }
.app-tile label { font-size: 11px; color: #e8efff; }
.launcher button { background: transparent; border: 0; color: #c8d7f5; border-radius: 9px; }
.launcher button:hover { background: rgba(126,165,255,0.17); }
.launcher .active-tab { background: rgba(96,151,255,0.22); color: #ffffff; }
.launcher .favorite-button { font-size: 17px; min-height: 20px; color: #a9c5ff; }
.launcher .app-button { padding: 0; }
.launcher .app-button:hover { background: rgba(126,165,255,0.17); }
"#;

fn populate(grid: &FlowBox, query: &str, window: &ApplicationWindow, count: &Label, favorites_only: bool, favorites: &Rc<std::cell::RefCell<HashSet<String>>>) {
    while let Some(child) = grid.first_child() {
        if let Ok(row) = child.downcast::<gtk::FlowBoxChild>() {
            grid.remove(&row);
        } else {
            break;
        }
    }
    let needle = query.trim().to_lowercase();
    let mut apps = gio::AppInfo::all();
    apps.retain(|app| app.should_show());
    if favorites_only {
        apps.retain(|app| app.id().is_some_and(|id| favorites.borrow().contains(id.as_str())));
    }
    apps.sort_by_key(|app| app.display_name().to_lowercase());
    let mut found: usize = 0;
    for info in apps {
        let name = info.display_name().to_string();
        let description = info.description().map(|s| s.to_string()).unwrap_or_default();
        if !needle.is_empty()
            && !name.to_lowercase().contains(&needle)
            && !description.to_lowercase().contains(&needle)
        {
            continue;
        }
        found += 1;
        let tile = GtkBox::new(Orientation::Vertical, 5);
        tile.add_css_class("app-tile");
        tile.set_halign(gtk::Align::Center);
        let icon = Image::new();
        if let Some(gicon) = info.icon() {
            icon.set_from_gicon(&gicon);
        } else {
            icon.set_icon_name(Some("application-x-executable-symbolic"));
        }
        let label = Label::new(Some(&name));
        label.set_max_width_chars(14);
        label.set_ellipsize(gtk::pango::EllipsizeMode::End);
        label.set_tooltip_text(Some(&name));
        tile.append(&icon);
        tile.append(&label);
        if let Some(id) = info.id() {
            let id = id.to_string();
            let favorite_button = Button::with_label(if favorites.borrow().contains(&id) { "★" } else { "☆" });
            favorite_button.set_tooltip_text(Some("Добавить или убрать из избранного"));
            favorite_button.add_css_class("favorite-button");
            let favorites = favorites.clone();
            let grid = grid.clone();
            let window = window.clone();
            let count = count.clone();
            let query = query.to_string();
            favorite_button.connect_clicked(move |_| {
                {
                    let mut current = favorites.borrow_mut();
                    if !current.insert(id.clone()) { current.remove(&id); }
                    if let Err(error) = save_favorites(&current) {
                        eprintln!("Failed to save favorites: {error}");
                    }
                }
                populate(&grid, &query, &window, &count, favorites_only, &favorites);
            });
            tile.append(&favorite_button);
        }
        let button = Button::new();
        button.add_css_class("app-button");
        button.set_child(Some(&tile));
        let app_info = info.clone();
        let close_window = window.clone();
        button.connect_clicked(move |_| {
            if let Err(error) = app_info.launch(&[], None::<&gio::AppLaunchContext>) {
                eprintln!("Failed to launch application: {error}");
            } else {
                close_window.close();
            }
        });
        grid.insert(&button, -1);
    }
    count.set_text(&format!("{found} приложений"));
}

fn main() {
    let app = Application::builder().application_id("cloud.localzet.Launcher").build();
    app.connect_activate(|app| {
        let window = ApplicationWindow::builder()
            .application(app).title("Localzet · Приложения")
            .default_width(520).default_height(470).build();
        window.init_layer_shell();
        window.set_layer(Layer::Overlay);
        window.set_anchor(Edge::Top, true);
        window.set_margin(Edge::Top, 44);
        window.set_keyboard_mode(KeyboardMode::Exclusive);
        window.set_namespace("localzet-launcher");

        let root = GtkBox::new(Orientation::Vertical, 12);
        root.add_css_class("launcher");
        let title = Label::new(Some("LOCALZET · ПРИЛОЖЕНИЯ"));
        title.add_css_class("heading");
        title.set_xalign(0.0);
        root.append(&title);

        let search = Entry::builder()
            .placeholder_text("Поиск приложений…")
            .build();
        root.append(&search);

        let tabs = GtkBox::new(Orientation::Horizontal, 6);
        let all_button = Button::with_label("Все приложения");
        let favorites_button = Button::with_label("Быстрый доступ");
        tabs.append(&all_button);
        tabs.append(&favorites_button);
        root.append(&tabs);
        all_button.add_css_class("active-tab");

        let grid = FlowBox::new();
        grid.set_selection_mode(gtk::SelectionMode::None);
        grid.set_max_children_per_line(4);
        grid.set_min_children_per_line(4);
        grid.set_row_spacing(5);
        grid.set_column_spacing(5);
        grid.set_homogeneous(true);

        let scroll = ScrolledWindow::builder()
            .vexpand(true).hscrollbar_policy(gtk::PolicyType::Never)
            .child(&grid).build();
        root.append(&scroll);

        let footer = GtkBox::new(Orientation::Horizontal, 8);
        let count = Label::new(None);
        count.add_css_class("hint");
        footer.append(&count);
        let spacer = GtkBox::new(Orientation::Horizontal, 0);
        spacer.set_hexpand(true);
        footer.append(&spacer);
        let close = Button::with_label("Закрыть  Esc");
        let close_window = window.clone();
        close.connect_clicked(move |_| close_window.close());
        footer.append(&close);
        root.append(&footer);

        let provider = gtk::CssProvider::new();
        provider.load_from_data(STYLE);
        if let Some(display) = gtk::gdk::Display::default() {
            gtk::style_context_add_provider_for_display(
                &display, &provider, gtk::STYLE_PROVIDER_PRIORITY_APPLICATION,
            );
        }

        window.set_child(Some(&root));
        let favorites_only = Rc::new(Cell::new(false));
        let favorites = Rc::new(std::cell::RefCell::new(load_favorites()));
        populate(&grid, "", &window, &count, false, &favorites);
        let list = grid.clone();
        let target = window.clone();
        let counter = count.clone();
        let current_filter = favorites_only.clone();
        let current_favorites = favorites.clone();
        search.connect_changed(move |entry| populate(&list, entry.text().as_str(), &target, &counter, current_filter.get(), &current_favorites));

        for (button, other_button, only_favorites) in [(all_button.clone(), favorites_button.clone(), false), (favorites_button, all_button, true)] {
            let list = grid.clone();
            let target = window.clone();
            let counter = count.clone();
            let search = search.clone();
            let filter = favorites_only.clone();
            let favorites = favorites.clone();
            button.connect_clicked(move |clicked| {
                clicked.add_css_class("active-tab");
                other_button.remove_css_class("active-tab");
                filter.set(only_favorites);
                populate(&list, search.text().as_str(), &target, &counter, only_favorites, &favorites);
                search.grab_focus();
            });
        }

        let key = gtk::EventControllerKey::new();
        let target = window.clone();
        key.connect_key_pressed(move |_, key, _, _| {
            if key == gtk::gdk::Key::Escape {
                target.close();
                return glib::Propagation::Stop;
            }
            glib::Propagation::Proceed
        });
        window.add_controller(key);
        window.present();
        search.grab_focus();
    });
    app.run();
}
