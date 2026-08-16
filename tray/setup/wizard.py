"""
wizard.py -- OnboardingWizard: window shell, stack, navigation.

Page build() functions may return either:
  - a Gtk.Widget  (content only, no footer)
  - a (Gtk.Widget, Gtk.Widget) tuple  (content, footer)

Footer widgets are placed in a fixed zone between the scroll area and the
nav buttons -- they are never scrolled away.
"""
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from .common import CSS, PAGES, SKIPPABLE, SENTINEL, TITLES, STEP_TAGS, lbl, sp
from .widgets import IllustrationArea, StepperDots

# Page builders
from . import (
    welcome, components, requirements, hud_try,
    tray_intro, makima_intro, tray_menu,
    setup_step1, setup_step2, trackpad_right, trackpad_left,
    desktop_icon, steam_updates_info, per_app_config, done,
)

_BUILDERS = {
    "welcome":            welcome.build,
    "components":         components.build,
    "requirements":       requirements.build,
    "hud_try":            hud_try.build,
    "tray_intro":         tray_intro.build,
    "tray_menu":          tray_menu.build,
    "makima_intro":       makima_intro.build,
    "setup_step1":        setup_step1.build,
    "setup_step2":        setup_step2.build,
    "trackpad_right":     trackpad_right.build,
    "trackpad_left":      trackpad_left.build,
    "desktop_icon":       desktop_icon.build,
    "steam_updates_info": steam_updates_info.build,
    "per_app_config":     per_app_config.build,
    "done":               done.build,
}


class OnboardingWizard:
    def __init__(self, on_done=None):
        self._on_done  = on_done
        self._page_idx = 0
        self._footers  = {}   # page_id -> Gtk.Widget | None

        self._win = Gtk.Window(title="Deckery Setup")
        self._win.set_default_size(832, 520)
        self._win.set_resizable(False)
        self._win.connect("destroy", self._on_close)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._win.add(root)

        self._illus = IllustrationArea()
        root.pack_start(self._illus, False, False, 0)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        right.get_style_context().add_class("wizard-right")
        root.pack_start(right, True, True, 0)

        self._stepper = StepperDots(len(PAGES))
        right.pack_start(self._stepper, False, False, 0)
        right.pack_start(sp(6), False, False, 0)

        # Fixed page header (step-tag + title, never scrolls)
        self._step_tag_lbl = lbl("", "step-tag", wrap=False)
        self._step_tag_lbl.set_no_show_all(True)
        right.pack_start(self._step_tag_lbl, False, False, 0)

        self._title_lbl = lbl("", "page-title", wrap=False)
        right.pack_start(self._title_lbl, False, False, 0)
        right.pack_start(sp(8), False, False, 0)

        # Scrollable content area
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self._stack.set_homogeneous(False)
        scroll.add(self._stack)
        right.pack_start(scroll, True, True, 0)

        # Build all pages; collect optional footer widgets
        for page_id in PAGES:
            result = _BUILDERS[page_id]()
            if isinstance(result, tuple):
                content, footer = result
            else:
                content, footer = result, None
            self._stack.add_named(content, page_id)
            self._footers[page_id] = footer

        # Fixed footer zone (between scroll and nav buttons)
        self._footer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._footer_box.set_no_show_all(True)
        self._footer_box.set_margin_top(16)
        right.pack_start(self._footer_box, False, False, 0)
        self._footer_vis_handler = None   # signal ID for lazy-footer tracking

        # Navigation buttons
        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        nav.set_margin_top(6)
        right.pack_start(nav, False, False, 0)

        self._btn_back = Gtk.Button(label="Back")
        self._btn_back.get_style_context().add_class("btn-back")
        self._btn_back.set_relief(Gtk.ReliefStyle.NONE)
        self._btn_back.set_no_show_all(True)
        self._btn_back.connect("clicked", self._on_back)

        self._btn_skip = Gtk.Button(label="Skip")
        self._btn_skip.get_style_context().add_class("btn-skip")
        self._btn_skip.set_relief(Gtk.ReliefStyle.NONE)
        self._btn_skip.set_no_show_all(True)
        self._btn_skip.connect("clicked", self._on_skip)

        self._btn_next = Gtk.Button(label="Next")
        self._btn_next.get_style_context().add_class("btn-primary")
        self._btn_next.set_relief(Gtk.ReliefStyle.NONE)
        self._btn_next.connect("clicked", self._on_next)

        nav.pack_start(self._btn_back, False, False, 0)
        nav.pack_start(self._btn_skip, False, False, 0)
        nav.pack_end(self._btn_next,   False, False, 0)

        self._update_ui()

    def show(self):
        self._win.show_all()
        # Footers are not in tree yet; show current page footer after show_all
        self._swap_footer(PAGES[self._page_idx])

    def _on_next(self, _b):
        if self._page_idx < len(PAGES) - 1:
            self._page_idx += 1
            self._update_ui()
        else:
            self._finish()

    def _on_back(self, _b):
        if self._page_idx > 0:
            self._page_idx -= 1
            self._update_ui()

    def _on_skip(self, _b):
        self._on_next(None)

    def _on_close(self, _w):
        if self._on_done:
            self._on_done()

    def _swap_footer(self, page: str):
        """Remove current footer child and insert the one for page (if any)."""
        # Disconnect old lazy-visibility handler
        old_children = self._footer_box.get_children()
        if self._footer_vis_handler is not None and old_children:
            try:
                old_children[0].disconnect(self._footer_vis_handler)
            except Exception:
                pass
            self._footer_vis_handler = None

        for child in self._footer_box.get_children():
            self._footer_box.remove(child)

        footer = self._footers.get(page)
        if footer is not None:
            self._footer_box.pack_start(footer, False, False, 0)
            if footer.get_no_show_all():
                # Footer manages its own visibility (lazy reveal)
                self._footer_box.set_visible(footer.get_visible())
                self._footer_vis_handler = footer.connect(
                    "notify::visible",
                    lambda w, _: self._footer_box.set_visible(w.get_visible()),
                )
            else:
                self._footer_box.set_visible(True)
                footer.show_all()
        else:
            self._footer_box.set_visible(False)

    def _update_ui(self):
        page = PAGES[self._page_idx]
        self._stack.set_visible_child_name(page)
        self._illus.set_page(page)
        self._stepper.set_index(self._page_idx)
        last = self._page_idx == len(PAGES) - 1
        self._btn_next.set_label("Finish" if last else "Next")
        self._btn_back.set_visible(self._page_idx > 0)
        self._btn_skip.set_visible(page in SKIPPABLE)
        self._swap_footer(page)
        # Update fixed header
        step_tag = STEP_TAGS.get(page, "")
        self._step_tag_lbl.set_text(step_tag)
        self._step_tag_lbl.set_visible(bool(step_tag))
        self._title_lbl.set_text(TITLES.get(page, ""))

    def _finish(self):
        os.makedirs(os.path.dirname(SENTINEL), exist_ok=True)
        open(SENTINEL, "w").close()
        self._win.destroy()
        if self._on_done:
            self._on_done()
