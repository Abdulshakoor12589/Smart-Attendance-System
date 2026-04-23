# theme.py — Theme system with 5 custom palettes
import json, os, sys

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_data_dir():
    """Writable dir — next to .exe when installed, project dir when dev."""
    import sys, os
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

THEME_FILE = os.path.join(get_data_dir(), "app_settings.json")

# ── 5 Themes from user palettes ───────────────────────────────────────────────
THEMES = {

    # Image 1 — Steel Blue: #020b17 #111827 #1f2937 #9ca3af #e5e7eb
    "Steel Blue": {
        "bg":            "#020b17",
        "panel":         "#111827",
        "panel2":        "#1f2937",
        "accent":        "#9ca3af",
        "accent2":       "#e5e7eb",
        "text":          "#e5e7eb",
        "text_dim":      "#9ca3af",
        "entry_bg":      "#111827",
        "entry_border":  "#1f2937",
        "btn_primary":   "#1f2937",
        "btn_danger":    "#7f1d1d",
        "header_grad1":  "#020b17",
        "header_grad2":  "#111827",
        "brand_grad1":   "#111827",
        "brand_grad2":   "#1f2937",
        "card1_g1":      "#111827",  "card1_g2": "#1f2937",
        "card2_g1":      "#0f172a",  "card2_g2": "#1e293b",
        "card3_g1":      "#1f2937",  "card3_g2": "#374151",
        "card4_g1":      "#0c1523",  "card4_g2": "#1f2937",
        "nav_strip":     "#1f2937",
        "nav_active":    "#9ca3af",
        "footer_g1":     "#020b17",  "footer_g2": "#111827",
    },

    # Image 2 — Deep Forest: #000505 #101615 #1e2f2a #3c5f4d #8fa99a
    "Deep Forest": {
        "bg":            "#000505",
        "panel":         "#101615",
        "panel2":        "#1e2f2a",
        "accent":        "#8fa99a",
        "accent2":       "#3c5f4d",
        "text":          "#d4e8df",
        "text_dim":      "#8fa99a",
        "entry_bg":      "#101615",
        "entry_border":  "#1e2f2a",
        "btn_primary":   "#1e2f2a",
        "btn_danger":    "#5f1a1a",
        "header_grad1":  "#000505",
        "header_grad2":  "#101615",
        "brand_grad1":   "#101615",
        "brand_grad2":   "#1e2f2a",
        "card1_g1":      "#101615",  "card1_g2": "#1e2f2a",
        "card2_g1":      "#0a1210",  "card2_g2": "#1e2f2a",
        "card3_g1":      "#1e2f2a",  "card3_g2": "#3c5f4d",
        "card4_g1":      "#0a1a10",  "card4_g2": "#1e2f2a",
        "nav_strip":     "#1e2f2a",
        "nav_active":    "#8fa99a",
        "footer_g1":     "#000505",  "footer_g2": "#101615",
    },

    # Image 3 — Graphite: #222222 #3B3B3B #515151 #7E7E7E #E1E1E1
    "Graphite": {
        "bg":            "#1a1a1a",
        "panel":         "#222222",
        "panel2":        "#3b3b3b",
        "accent":        "#cfcfcf",
        "accent2":       "#9e9e9e",
        "text":          "#f7f7f7",
        "text_dim":      "#9e9e9e",
        "entry_bg":      "#2a2a2a",
        "entry_border":  "#515151",
        "btn_primary":   "#3b3b3b",
        "btn_danger":    "#7f1d1d",
        "header_grad1":  "#1a1a1a",
        "header_grad2":  "#222222",
        "brand_grad1":   "#222222",
        "brand_grad2":   "#3b3b3b",
        "card1_g1":      "#222222",  "card1_g2": "#3b3b3b",
        "card2_g1":      "#1a1a1a",  "card2_g2": "#3b3b3b",
        "card3_g1":      "#3b3b3b",  "card3_g2": "#515151",
        "card4_g1":      "#222222",  "card4_g2": "#515151",
        "nav_strip":     "#3b3b3b",
        "nav_active":    "#e1e1e1",
        "footer_g1":     "#1a1a1a",  "footer_g2": "#222222",
    },

    # Image 4 — Royal Purple: dark purple #1a0533 + mid #4a2080 + bright #7c3aed
    "Royal Purple": {
        "bg":            "#0d0118",
        "panel":         "#1a0533",
        "panel2":        "#2d0f5e",
        "accent":        "#a855f7",
        "accent2":       "#7c3aed",
        "text":          "#ede9fe",
        "text_dim":      "#a78bfa",
        "entry_bg":      "#1a0533",
        "entry_border":  "#2d0f5e",
        "btn_primary":   "#2d0f5e",
        "btn_danger":    "#7f1d1d",
        "header_grad1":  "#0d0118",
        "header_grad2":  "#1a0533",
        "brand_grad1":   "#1a0533",
        "brand_grad2":   "#2d0f5e",
        "card1_g1":      "#1a0533",  "card1_g2": "#2d0f5e",
        "card2_g1":      "#0d0118",  "card2_g2": "#2d0f5e",
        "card3_g1":      "#2d0f5e",  "card3_g2": "#4a2080",
        "card4_g1":      "#1a0533",  "card4_g2": "#3b1080",
        "nav_strip":     "#2d0f5e",
        "nav_active":    "#a855f7",
        "footer_g1":     "#0d0118",  "footer_g2": "#1a0533",
    },

    # Image 5 — Coffee: #1c0a0a #3b1a0a #7b4a2a #c8956c #e8d5b7
    "Coffee": {
        "bg":            "#1c0a0a",
        "panel":         "#2a1208",
        "panel2":        "#3b1a0a",
        "accent":        "#c8956c",
        "accent2":       "#e8d5b7",
        "text":          "#f5ebe0",
        "text_dim":      "#c8956c",
        "entry_bg":      "#2a1208",
        "entry_border":  "#3b1a0a",
        "btn_primary":   "#3b1a0a",
        "btn_danger":    "#7f1d1d",
        "header_grad1":  "#1c0a0a",
        "header_grad2":  "#2a1208",
        "brand_grad1":   "#2a1208",
        "brand_grad2":   "#3b1a0a",
        "card1_g1":      "#2a1208",  "card1_g2": "#3b1a0a",
        "card2_g1":      "#1c0a0a",  "card2_g2": "#3b1a0a",
        "card3_g1":      "#3b1a0a",  "card3_g2": "#5c2d12",
        "card4_g1":      "#2a1208",  "card4_g2": "#7b4a2a",
        "nav_strip":     "#3b1a0a",
        "nav_active":    "#c8956c",
        "footer_g1":     "#1c0a0a",  "footer_g2": "#2a1208",
    },
}

# ── Runtime ───────────────────────────────────────────────────────────────────
_current   = THEMES["Steel Blue"].copy()
_name      = "Steel Blue"
_listeners = []


def load():
    global _current, _name
    try:
        with open(THEME_FILE) as f:
            s = json.load(f)
        name = s.get("theme", "Steel Blue")
        if name in THEMES:
            _current = THEMES[name].copy()
            _name    = name
    except:
        pass


def save(name):
    global _current, _name
    try:
        try:
            with open(THEME_FILE) as f:
                s = json.load(f)
        except:
            s = {}
        s["theme"] = name
        with open(THEME_FILE, 'w') as f:
            json.dump(s, f, indent=2)
        if name in THEMES:
            _current = THEMES[name].copy()
            _name    = name
        _notify()
    except Exception as e:
        print(f"Theme save error: {e}")


def get(key, fallback="#111827"):
    return _current.get(key, fallback)


def name():
    return _name


def all_names():
    return list(THEMES.keys())


def add_listener(cb):
    if cb not in _listeners:
        _listeners.append(cb)


def remove_listener(cb):
    if cb in _listeners:
        _listeners.remove(cb)


def _notify():
    for cb in list(_listeners):
        try: cb()
        except: pass


load()