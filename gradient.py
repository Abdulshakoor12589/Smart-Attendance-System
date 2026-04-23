# gradient.py - Horizontal gradient utility for tkinter
import tkinter as tk


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r, g, b):
    return f'#{int(r):02x}{int(g):02x}{int(b):02x}'


def make_gradient(canvas, width, height, color1, color2, direction='horizontal'):
    """Draw a gradient on a canvas from color1 to color2."""
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)

    steps = width if direction == 'horizontal' else height
    for i in range(steps):
        t = i / max(steps - 1, 1)
        r = r1 + (r2 - r1) * t
        g = g1 + (g2 - g1) * t
        b = b1 + (b2 - b1) * t
        color = rgb_to_hex(r, g, b)
        if direction == 'horizontal':
            canvas.create_line(i, 0, i, height, fill=color)
        else:
            canvas.create_line(0, i, width, i, fill=color)


class GradientFrame(tk.Canvas):
    """A frame-like canvas with a horizontal gradient background."""
    def __init__(self, parent, color1, color2, height=60,
                 direction='horizontal', **kwargs):
        super().__init__(parent, height=height,
                         highlightthickness=0, bd=0, **kwargs)
        self.color1    = color1
        self.color2    = color2
        self.direction = direction
        self._drawn    = False
        self.bind('<Configure>', self._on_resize)

    def _on_resize(self, event):
        self.delete('all')
        w, h = event.width, event.height
        r1, g1, b1 = hex_to_rgb(self.color1)
        r2, g2, b2 = hex_to_rgb(self.color2)
        steps = w if self.direction == 'horizontal' else h
        for i in range(steps):
            t = i / max(steps - 1, 1)
            r = r1 + (r2 - r1) * t
            g = g1 + (g2 - g1) * t
            b = b1 + (b2 - b1) * t
            color = rgb_to_hex(r, g, b)
            if self.direction == 'horizontal':
                self.create_line(i, 0, i, h, fill=color, tags='gradient')
            else:
                self.create_line(0, i, w, i, fill=color, tags='gradient')
        # Lift all non-gradient items above the gradient
        self.tag_raise('widgets')
        self.tag_lower('gradient')

    def add_label(self, text, font, fg, anchor='center', x=None, y=None):
        """Add text label on top of gradient."""
        self.update_idletasks()
        cx = x if x is not None else self.winfo_width() // 2
        cy = y if y is not None else self.winfo_height() // 2
        self.create_text(cx, cy, text=text, font=font,
                          fill=fg, anchor=anchor, tags='widgets')


class GradientButton(tk.Canvas):
    """A button with horizontal gradient background."""
    def __init__(self, parent, text, color1, color2,
                 command=None, font=("Inter 18pt", 11, "bold"),
                 fg='white', padx=18, pady=8,
                 hover_color1=None, hover_color2=None,
                 width=200, height=40, **kwargs):
        super().__init__(parent, width=width, height=height,
                         highlightthickness=0, bd=0,
                         cursor='hand2', **kwargs)
        self.color1      = color1
        self.color2      = color2
        self.hcolor1     = hover_color1 or color2
        self.hcolor2     = hover_color2 or color1
        self.text        = text
        self.font        = font
        self.fg          = fg
        self.command     = command
        self._hovered    = False

        self.bind('<Configure>', self._draw)
        self.bind('<Enter>',     self._on_enter)
        self.bind('<Leave>',     self._on_leave)
        self.bind('<Button-1>',  self._on_click)

    def _draw(self, event=None):
        self.delete('all')
        w = self.winfo_width()  or int(self['width'])
        h = self.winfo_height() or int(self['height'])
        c1 = self.hcolor1 if self._hovered else self.color1
        c2 = self.hcolor2 if self._hovered else self.color2
        r1, g1, b1 = hex_to_rgb(c1)
        r2, g2, b2 = hex_to_rgb(c2)
        for i in range(w):
            t = i / max(w - 1, 1)
            color = rgb_to_hex(
                r1 + (r2 - r1) * t,
                g1 + (g2 - g1) * t,
                b1 + (b2 - b1) * t)
            self.create_line(i, 0, i, h, fill=color)
        self.create_text(w // 2, h // 2, text=self.text,
                          font=self.font, fill=self.fg, anchor='center')

    def _on_enter(self, e):
        self._hovered = True;  self._draw()

    def _on_leave(self, e):
        self._hovered = False; self._draw()

    def _on_click(self, e):
        if self.command:
            self.command()

    def config_state(self, state):
        if state == tk.DISABLED:
            self.unbind('<Button-1>')
            self.configure(cursor='arrow')
        else:
            self.bind('<Button-1>', self._on_click)
            self.configure(cursor='hand2')