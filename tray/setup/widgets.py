"""
widgets.py -- Shared custom GTK widgets: illustration panel, stepper dots, L3 visual.
"""
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf
import cairo

from .common import C_BG, C_TEAL, C_AMBER, HUD_ASSETS


class IllustrationArea(Gtk.DrawingArea):
    """Left panel -- Cairo-rendered Steam Deck illustration with per-page overlays."""

    def __init__(self):
        super().__init__()
        self.set_size_request(240, -1)
        self._page = "welcome"
        self._svg  = self._load("steamdeckFront.svg")
        self.connect("draw", self._on_draw)

    def set_page(self, page: str):
        self._page = page
        self.queue_draw()

    def _load(self, name: str):
        try:
            return GdkPixbuf.Pixbuf.new_from_file(os.path.join(HUD_ASSETS, name))
        except Exception:
            return None

    def _on_draw(self, _w, cr: cairo.Context):
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        TAU = 2 * 3.14159

        # Background gradient
        grad = cairo.LinearGradient(0, 0, 0, h)
        grad.add_color_stop_rgb(0, 0.04, 0.04, 0.10)
        grad.add_color_stop_rgb(1, *C_BG)
        cr.set_source(grad)
        cr.paint()

        # Ambient glow
        cx, cy = w / 2, h / 2 - 20
        g = cairo.RadialGradient(cx, cy, 0, cx, cy, 130)
        g.add_color_stop_rgba(0, *C_TEAL, 0.07)
        g.add_color_stop_rgba(1, *C_TEAL, 0.0)
        cr.set_source(g)
        cr.arc(cx, cy, 130, 0, TAU)
        cr.fill()

        # Page overlay (behind deck SVG so the glow is visible through it)
        self._overlay(cr, w, h)

        # Steam Deck SVG
        if self._svg:
            pb = self._svg
            scale = min((w - 50) / pb.get_width(), (h - 90) / pb.get_height())
            x = (w - pb.get_width()  * scale) / 2
            y = (h - pb.get_height() * scale) / 2 - 8
            cr.save()
            cr.translate(x, y)
            cr.scale(scale, scale)
            Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
            cr.paint_with_alpha(0.88)
            cr.restore()

        # Bottom border
        cr.set_source_rgba(*C_TEAL, 0.18)
        cr.set_line_width(1)
        cr.move_to(0, h - 1)
        cr.line_to(w, h - 1)
        cr.stroke()

    def _overlay(self, cr, w, h):
        TAU = 2 * 3.14159

        def teal_glow(rx, ry, r, alpha=0.30):
            cx2, cy2 = w * rx, h * ry
            g = cairo.RadialGradient(cx2, cy2, 0, cx2, cy2, r)
            g.add_color_stop_rgba(0, *C_TEAL, alpha)
            g.add_color_stop_rgba(1, *C_TEAL, 0.0)
            cr.set_source(g)
            cr.arc(cx2, cy2, r, 0, TAU)
            cr.fill()

        def amber_glow(rx, ry, r, alpha=0.28):
            cx2, cy2 = w * rx, h * ry
            g = cairo.RadialGradient(cx2, cy2, 0, cx2, cy2, r)
            g.add_color_stop_rgba(0, *C_AMBER, alpha)
            g.add_color_stop_rgba(1, *C_AMBER, 0.0)
            cr.set_source(g)
            cr.arc(cx2, cy2, r, 0, TAU)
            cr.fill()

        if self._page == "hud_try":
            # Left stick is at SVG ~(164, 90) in a 1024x414 SVG
            # rendered at scale ~0.186 into 240px wide panel -> ~(0.23, 0.44)
            teal_glow(0.23, 0.44, 55, 0.45)
            teal_glow(0.23, 0.44, 22, 0.60)

        elif self._page in ("tray_intro",):
            # Soft top-right glow suggesting the system tray
            teal_glow(0.72, 0.18, 55, 0.30)

        elif self._page == "makima_intro":
            amber_glow(0.50, 0.50, 70, 0.20)
            amber_glow(0.36, 0.59, 28, 0.30)   # left stick
            amber_glow(0.73, 0.45, 22, 0.28)   # face buttons

        elif self._page == "requirements":
            cx2, cy2 = w / 2, h * 0.72
            cr.set_source_rgba(*C_AMBER, 0.55)
            cr.arc(cx2, cy2, 15, 0, TAU)
            cr.fill()
            cr.set_source_rgba(*C_BG, 1)
            cr.arc(cx2, cy2, 8, 0, TAU)
            cr.fill()

        elif self._page == "setup_step1":
            amber_glow(0.83, 0.44, 22)   # X button position

        elif self._page == "setup_step2":
            amber_glow(0.73, 0.45, 38)

        elif self._page == "trackpad_right":
            teal_glow(0.73, 0.52, 40)

        elif self._page == "trackpad_left":
            teal_glow(0.27, 0.52, 40)


class StepperDots(Gtk.DrawingArea):
    """Progress indicator: one dot per page, active dot is teal."""

    def __init__(self, n: int):
        super().__init__()
        self._n   = n
        self._idx = 0
        self.set_size_request(-1, 20)
        self.connect("draw", self._on_draw)

    def set_index(self, idx: int):
        self._idx = idx
        self.queue_draw()

    def _on_draw(self, _w, cr):
        w       = self.get_allocated_width()
        spacing = 12
        total   = self._n * 6 + (self._n - 1) * (spacing - 6)
        x       = (w - total) / 2
        y       = 10
        for i in range(self._n):
            if i == self._idx:
                cr.set_source_rgba(*C_TEAL, 1.0)
                cr.arc(x + 3, y, 4, 0, 2 * 3.14159)
            else:
                cr.set_source_rgba(1, 1, 1, 0.15)
                cr.arc(x + 3, y, 2.5, 0, 2 * 3.14159)
            cr.fill()
            x += spacing


class L3Visual(Gtk.DrawingArea):
    """Cairo-drawn L3 button indicator, intended to be wrapped in an EventBox."""

    def __init__(self):
        super().__init__()
        self.set_size_request(72, 72)
        self.connect("draw", self._on_draw)

    def _on_draw(self, _w, cr):
        w, h  = self.get_allocated_width(), self.get_allocated_height()
        cx, cy = w / 2, h / 2
        TAU   = 2 * 3.14159

        g = cairo.RadialGradient(cx, cy, 16, cx, cy, 36)
        g.add_color_stop_rgba(0, *C_TEAL, 0.22)
        g.add_color_stop_rgba(1, *C_TEAL, 0.0)
        cr.set_source(g)
        cr.arc(cx, cy, 36, 0, TAU)
        cr.fill()

        cr.set_source_rgba(*C_TEAL, 0.70)
        cr.set_line_width(2)
        cr.arc(cx, cy, 26, 0, TAU)
        cr.stroke()

        cr.set_source_rgba(*C_TEAL, 0.95)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(14)
        te = cr.text_extents("L3")
        cr.move_to(cx - te.width / 2, cy + te.height / 2)
        cr.show_text("L3")
