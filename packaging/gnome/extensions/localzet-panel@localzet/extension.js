// SPDX-License-Identifier: MIT
import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const SYSTEM_INDICATORS = new Set([
    'localzet-asus', 'software-update-available', 'software_update_available',
    'livepatch', 'unattended-upgrade', 'unattended_upgrade',
]);

export default class PanelLayout extends Extension {
    enable() {
        this._original = new Map();
        this._sync();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 2, () => {
            this._sync();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _sync() {
        for (const [role, button] of Object.entries(Main.panel.statusArea)) {
            if (!role.startsWith('appindicator-') || !button?.container)
                continue;
            const actor = button.container;
            const parent = actor.get_parent();
            if (!parent)
                continue;
            const indicator = button._indicator;
            if (indicator && !indicator.id)
                continue;
            const hardware = SYSTEM_INDICATORS.has(indicator?.id);
            const target = hardware ? Main.panel._rightBox : Main.panel._leftBox;
            if (!this._original.has(actor)) {
                const destroyId = actor.connect('destroy', () => this._original.delete(actor));
                this._original.set(actor, {parent, index: parent.get_children().indexOf(actor), destroyId});
                actor.add_style_class_name('localzet-panel-item');
            }
            if (parent === target)
                continue;
            parent.remove_child(actor);
            if (hardware)
                target.insert_child_at_index(actor, 0);
            else
                target.add_child(actor);
        }
    }

    disable() {
        if (this._timer)
            GLib.Source.remove(this._timer);
        this._timer = 0;
        for (const [actor, {parent, index, destroyId}] of this._original) {
            actor.disconnect(destroyId);
            actor.remove_style_class_name('localzet-panel-item');
            const current = actor.get_parent();
            if (current && current !== parent) {
                current.remove_child(actor);
                parent.insert_child_at_index(actor, Math.min(index, parent.get_n_children()));
            }
        }
        this._original.clear();
    }
}
