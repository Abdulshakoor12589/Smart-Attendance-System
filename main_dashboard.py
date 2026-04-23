# main_dashboard.py - Gradients, no duplicate text
import tkinter as tk
from tkinter import messagebox
import os, sys
from database import Database
from register_student import RegisterStudentWindow
from teacher_dashboard import TeacherDashboard
from attendance_teacher import TeacherAttendanceWindow
from report import ReportWindow
from registered_students import RegisteredStudentsWindow
from settings import SettingsPanel
import fp_session
import theme as TM
from gradient import GradientFrame, GradientButton
from PIL import Image, ImageTk, ImageFilter, ImageEnhance


def get_base_dir():
    if getattr(sys, 'frozen', False):
        # PyInstaller stores files in _MEIPASS when running as .exe
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))
def _set_app_icon(win):
    """Set favicon.png as window icon."""
    base = get_base_dir()
    for name in ["favicon.png", "favicon.ico"]:
        path = os.path.join(base, name)
        if os.path.exists(path):
            try:
                img = tk.PhotoImage(file=path)
                win.iconphoto(False, img)
                win._icon_ref = img  # prevent GC
            except: pass
            break



class MainDashboard:
    def __init__(self, admin_name):
        self.admin_name = admin_name
        self.root = tk.Tk()
        _set_app_icon(self.root)
        self.root.title("Smart Attendance System")
        self.root.resizable(True, True)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        W = min(1100, sw - 20)
        H = min(780, sh - 60)
        self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        self.root.minsize(800, 600)

        self.db = Database()
        import fonts as F; F.setup()
        self._refs = {}

        self._set_favicon()
        self._build_ui()

    def _img(self, filename, size):
        path = os.path.join(get_base_dir(), filename)
        if not os.path.exists(path): return None
        try:
            photo = ImageTk.PhotoImage(
                Image.open(path).convert("RGBA").resize(
                    size, Image.Resampling.LANCZOS))
            self._refs[filename] = photo
            return photo
        except: return None

    def _set_favicon(self):
        ico = self._img("favicon.png", (32, 32))
        if ico: self.root.iconphoto(True, ico)

    # ── build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.configure(bg=TM.get('bg','#0d0d1a'))

        # Background image
        self.bg_label = tk.Label(self.root, bd=0)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.bg_label.lower()
        self._load_bg_image()
        self.root.bind('<Configure>', self._on_resize)

        self.main = tk.Frame(self.root, bg=TM.get('bg','#0d0d1a'))
        self.main.pack(fill=tk.BOTH, expand=True)

        # ── Persistent Header ─────────────────────────────────────────────────
        self.hdr = GradientFrame(self.main, TM.get('header_grad1','#0d0d2e'), TM.get('header_grad2','#0a2a2a'), height=70)
        self.hdr.pack(fill=tk.X)

        logo = self._img("favicon.png", (46, 46))
        self.logo_lbl = None
        if logo:
            self.logo_lbl = tk.Label(self.hdr, image=logo, bg='#0d0d2e', bd=0)
            self.logo_lbl.place(x=15, y=12)

        # ← Back button — sits at SAME place as logo, hidden on home
        self.back_btn = tk.Button(self.hdr, text=" ←",
            font=("Inter 18pt", 18, "bold"),
            bg=TM.get('header_grad1','#0d0d2e'), fg=TM.get('accent','#00E5CC'),
            relief=tk.FLAT, cursor='hand2', bd=0,
            activebackground='#0d0d2e', activeforeground='white',
            command=self._go_home)
        self.back_btn.place_forget()   # hidden initially

        # Page title in header
        self.page_title_lbl = tk.Label(self.hdr, text="",
            font=("Inter 18pt", 13, "bold"),
            bg=TM.get('header_grad1','#0d0d2e'), fg=TM.get('accent','#00E5CC'))
        self.page_title_lbl.place(x=70, y=20)

        # Right side
        right_f = tk.Frame(self.hdr, bg=TM.get('header_grad1','#0d0d2e'))
        right_f.place(relx=1.0, x=-310, y=15, anchor='nw')

        tk.Label(right_f, text=f"👤 {self.admin_name}",
                 font=("Roboto", 11), bg=TM.get('header_grad1','#0d0d2e'), fg=TM.get('text','#BDC3C7')
                 ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(right_f, text="⚙️", font=("Roboto", 13),
                  bg=TM.get('header_grad1','#0d0d2e'), fg=TM.get('text','white'), relief=tk.FLAT,
                  cursor='hand2', activebackground=TM.get('panel','#1a2a4e'),
                  command=self._open_settings).pack(side=tk.LEFT, padx=(0, 10))

        logout_btn = GradientButton(
            right_f, text="🚪 Logout",
            color1=TM.get('btn_danger','#C0392B'), color2=TM.get('btn_danger','#7B241C'),
            hover_color1=TM.get('accent','#E74C3C'), hover_color2=TM.get('btn_danger','#C0392B'),
            command=self._logout, width=110, height=36)
        logout_btn.pack(side=tk.LEFT)

        # ── Content area (swaps between home and sub-pages) ───────────────────
        self.content = tk.Frame(self.main, bg=TM.get('bg','#0d0d1a'))
        self.content.pack(fill=tk.BOTH, expand=True)

        # ── Footer ────────────────────────────────────────────────────────────
        self.footer = GradientFrame(self.main, TM.get('footer_g1','#0d0d2e'), TM.get('footer_g2','#001a1a'), height=28)
        self.footer.pack(fill=tk.X, side=tk.BOTTOM)
        self.footer.bind('<Configure>', self._draw_footer)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Show home page
        self._show_home()

    def _show_home(self):
        """Render the home dashboard inside self.content."""
        for w in self.content.winfo_children():
            w.destroy()

        # Restore logo, hide back button and page title
        self._close_settings_panel()
        self.back_btn.place_forget()
        self.page_title_lbl.config(text="")
        if hasattr(self, 'logo_lbl') and self.logo_lbl:
            self.logo_lbl.place(x=15, y=12)

        # ── Brand strip ───────────────────────────────────────────────────────
        brand = GradientFrame(self.content, TM.get('brand_grad1','#0d0d2e'), TM.get('brand_grad2','#001a1a'), height=72)
        brand.pack(fill=tk.X)
        brand.bind('<Configure>', self._draw_brand)

        # ── Shortcut nav bar ──────────────────────────────────────────────────
        strip = tk.Frame(self.content, bg=TM.get('nav_strip','#0f5c32'), height=42)
        strip.pack(fill=tk.X)
        strip.pack_propagate(False)

        nav_items = [
            ("📝  Register Student",   self._open_register),
            ("🏫  Teacher Dashboard",  self._open_attendance),
            ("📷  Door Attendance",    self._open_door),
            ("📊  Reports & History",  self._open_reports),
        ]
        for text, cmd in nav_items:
            btn = tk.Button(strip, text=text,
                font=("Inter 18pt", 10, "bold"),
                bg=TM.get('nav_strip','#0f5c32'), fg=TM.get('text','white'),
                activebackground='#00E5CC', activeforeground='#0d0d1a',
                relief=tk.FLAT, cursor='hand2', command=cmd)
            btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            btn.bind('<Enter>', lambda e, b=btn: b.config(bg=TM.get('nav_active','#00E5CC'), fg=TM.get('bg','#0d0d1a')))
            btn.bind('<Leave>', lambda e, b=btn: b.config(bg=TM.get('nav_strip','#0f5c32'), fg='white'))

        tk.Frame(self.content, bg='#00E5CC', height=2).pack(fill=tk.X)

        # ── Cards grid ────────────────────────────────────────────────────────
        co = tk.Frame(self.content, bg=TM.get('bg','#0d0d1a'))
        co.pack(fill=tk.BOTH, expand=True)
        co.columnconfigure(0, weight=1)
        co.columnconfigure(1, weight=1)
        co.rowconfigure(0, weight=1)
        co.rowconfigure(1, weight=1)

        cards = [
            ("📝", "REGISTER STUDENT",
             "Add new students with photo & details",
             TM.get('card1_g1','#1a6b3a'), TM.get('card1_g2','#0d4a5a'),
             TM.get('accent','#27AE60'), TM.get('accent2','#0a8a7a'),
             self._open_register),
            ("📷", "DOOR ATTENDANCE",
             "Start face recognition attendance session",
             TM.get('card2_g1','#1a3a6b'), TM.get('card2_g2','#0d2a5a'),
             TM.get('accent','#2980B9'), TM.get('accent2','#1a5a9a'),
             self._open_door),
            ("👥", "REGISTERED STUDENTS",
             "View, manage & delete students by semester",
             TM.get('card3_g1','#4a1a6b'), TM.get('card3_g2','#2d0a5a'),
             TM.get('accent','#7D3C98'), TM.get('accent2','#5a1a8a'),
             self._open_students),
            ("📊", "REPORTS & HISTORY",
             "View attendance logs and export CSV",
             TM.get('card4_g1','#6b3a0d'), TM.get('card4_g2','#5a2a0a'),
             TM.get('accent','#E67E22'), TM.get('accent2','#BA4A00'),
             self._open_reports),
        ]
        for idx, (icon, title, desc, c1, c2, h1, h2, cmd) in enumerate(cards):
            row, col = divmod(idx, 2)
            self._make_card(co, row, col, icon, title, desc, c1, c2, h1, h2, cmd)

    def _embed_page(self, title, PageClass, *args, **kwargs):
        """Render a page inside self.content. Pass content frame as container."""
        self._cleanup_embedded()
        self._close_settings_panel()

        # Clear content
        for w in self.content.winfo_children():
            w.destroy()

        # Create fresh container frame that fills content
        container = tk.Frame(self.content, bg='#0d0d1a')
        container.pack(fill=tk.BOTH, expand=True)

        # Instantiate page with container — page builds UI inside it
        page_obj = PageClass(self.root, container=container, *args, **kwargs)

        # Show ← back arrow where logo was, hide logo
        if hasattr(self, 'logo_lbl') and self.logo_lbl:
            self.logo_lbl.place_forget()
        self.back_btn.place(x=10, y=14)
        self.page_title_lbl.config(text=title)

        self._current_page = page_obj
        self._current_container = container

    def _cleanup_embedded(self):
        if hasattr(self, '_current_page') and self._current_page:
            try:
                p = self._current_page
                if hasattr(p, 'is_running'): p.is_running = False
                if hasattr(p, 'capture') and p.capture:
                    p.capture.release(); p.capture = None
            except: pass
            self._current_page = None
        if hasattr(self, '_current_container') and self._current_container:
            try: self._current_container.destroy()
            except: pass
            self._current_container = None

    def _go_home(self):
        self._cleanup_embedded()
        self._close_settings_panel()
        self._show_home()

    # ── draw callbacks (each deletes 'widgets' first) ─────────────────────────

    def _draw_brand(self, e):
        f = e.widget
        f._on_resize(e)
        f.delete('widgets')
        f.create_text(e.width//2, 26,
            text="SMART ATTENDANCE SYSTEM",
            font=("Inter 18pt", 16, "bold"), fill=TM.get('accent','#00E5CC'), tags='widgets')
        f.create_text(e.width//2, 52,
            text="Efficient. Secure. Automated.",
            font=("Roboto", 9, "italic"), fill=TM.get('accent2','#7ecdc4'), tags='widgets')

    def _draw_footer(self, e):
        self.footer._on_resize(e)
        self.footer.delete('widgets')
        self.footer.create_text(
            e.width // 2, 14,
            text="© 2024 Smart Attendance System  |  Data retained for 7 months",
            font=("Roboto", 8), fill='#7F8C8D', tags='widgets')

    # ── Card ──────────────────────────────────────────────────────────────────

    def _make_card(self, parent, row, col,
                   icon, title, desc, c1, c2, h1, h2, cmd):
        card = GradientFrame(parent, c1, c2)
        card.grid(row=row, column=col, sticky='nsew',
                  padx=(15 if col == 0 else 8, 8 if col == 0 else 15),
                  pady=(15 if row == 0 else 8, 8 if row == 0 else 15))
        card.config(cursor='hand2')

        # Store normal and hover colors
        card._c1, card._c2 = c1, c2
        card._h1, card._h2 = h1, h2

        def draw(e, c=card, i=icon, t=title, d=desc):
            c._on_resize(e)
            c.delete('widgets')
            cx, cy = e.width // 2, e.height // 2
            c.create_text(cx, cy - 52, text=i,
                          font=("Roboto", 32), fill='white', tags='widgets')
            c.create_text(cx, cy - 4,  text=t,
                          font=("Inter 18pt", 13, "bold"),
                          fill='white', tags='widgets')
            c.create_text(cx, cy + 32, text=d,
                          font=("Roboto", 10), fill='#FDFEFE',
                          justify=tk.CENTER, width=e.width - 40,
                          tags='widgets')

        def redraw(c=card, i=icon, t=title, d=desc):
            w = c.winfo_width(); h = c.winfo_height()
            if w < 2 or h < 2: return
            e = type('E', (), {'width': w, 'height': h})()
            draw(e, c, i, t, d)

        def on_enter(ev, c=card):
            c.color1, c.color2 = c._h1, c._h2
            redraw(c)

        def on_leave(ev, c=card):
            c.color1, c.color2 = c._c1, c._c2
            redraw(c)

        card.bind('<Configure>', draw)
        card.bind('<Enter>',     on_enter)
        card.bind('<Leave>',     on_leave)
        card.bind('<Button-1>',  lambda e, cm=cmd: cm())

    # ── Background ────────────────────────────────────────────────────────────

    def _load_bg_image(self, w=None, h=None):
        w = w or self.root.winfo_width()  or 1100
        h = h or self.root.winfo_height() or 780
        for name in ["tb.jpg", "tb.JPG"]:
            path = os.path.join(get_base_dir(), name)
            if os.path.exists(path):
                img = Image.open(path).resize((w, h), Image.Resampling.LANCZOS)
                img = ImageEnhance.Brightness(img).enhance(0.25)
                img = img.filter(ImageFilter.GaussianBlur(5))
                photo = ImageTk.PhotoImage(img)
                self._refs['bg'] = photo
                self.bg_label.config(image=photo)
                return

    def _on_resize(self, event):
        if event.widget == self.root:
            self._load_bg_image(event.width, event.height)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _open_register(self):
        self._embed_page("📝  Register Student", RegisterStudentWindow)
    def _open_attendance(self):
        self._embed_page("🏫  Teacher Dashboard", TeacherDashboard)
    def _open_door(self):
        self._embed_page("📷  Door Attendance", TeacherAttendanceWindow)
    def _open_students(self):
        self._embed_page("👥  Registered Students", RegisteredStudentsWindow)
    def _open_reports(self):
        self._embed_page("📊  Reports & History", ReportWindow)

    def _open_settings(self):
        """Toggle settings dropdown panel below the header."""
        if hasattr(self, '_settings_visible') and self._settings_visible:
            self._close_settings_panel()
        else:
            self._show_settings_panel()

    def _show_settings_panel(self):
        """Build inline settings panel directly inside a floating frame."""
        self._settings_visible = True
        if hasattr(self, '_settings_panel') and self._settings_panel:
            try: self._settings_panel.destroy()
            except: pass

        # Floating panel placed below gear icon (top-right)
        panel = tk.Frame(self.root, bg='#0d0d1a',
                          highlightthickness=1,
                          highlightbackground='#00E5CC',
                          width=460, height=580)
        panel.place(relx=1.0, x=-470, y=72)
        panel.pack_propagate(False)
        self._settings_panel = panel

        # ── Header row ────────────────────────────────────────────────────────
        ph = tk.Frame(panel, bg='#0d1a2e', height=40)
        ph.pack(fill=tk.X)
        ph.pack_propagate(False)
        tk.Label(ph, text="⚙   SETTINGS",
                 font=("Inter 18pt", 12, "bold"),
                 bg='#0d1a2e', fg='#00E5CC').pack(side=tk.LEFT, padx=14, pady=8)
        tk.Button(ph, text="✕",
                  font=("Roboto", 12, "bold"),
                  bg='#0d1a2e', fg='#7ecdc4',
                  relief=tk.FLAT, cursor='hand2',
                  activebackground='#C0392B', activeforeground='white',
                  command=self._close_settings_panel).pack(side=tk.RIGHT, padx=12)
        tk.Frame(panel, bg='#00E5CC', height=1).pack(fill=tk.X)

        # ── Scrollable body ───────────────────────────────────────────────────
        outer = tk.Frame(panel, bg='#0d0d1a')
        outer.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(outer, bg='#0d0d1a',
                            highlightthickness=0, bd=0)
        sb = tk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview,
                           bg='#1a1a2e', troughcolor='#0d0d1a')
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.configure(yscrollcommand=sb.set)
        body = tk.Frame(canvas, bg='#0d0d1a')
        canvas.create_window(0, 0, anchor='nw', window=body, width=460)
        body.bind('<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<MouseWheel>',
            lambda e: canvas.yview_scroll(-1*(e.delta//120), 'units'))

        # ── Menu items ────────────────────────────────────────────────────────
        MENU = [
            ("👤", "My Account",          "Change password, view profile",   '#1a2a4a', '#2980B9'),
            ("🎯", "Face Recognition",    "Camera & sensitivity settings",   '#1a3a1a', '#27ae60'),
            ("👆", "Fingerprint",         "Windows Hello & USB scanner",     '#2a1a4a', '#7D3C98'),
            ("🎨", "Display & Appearance","Themes & color palettes",         '#2a1a0a', '#E67E22'),
            ("🔒", "Privacy & Security",  "Data storage & backup",           '#2a1a3a', '#7D3C98'),
            ("❓", "Help & Support",      "About & system information",      '#1a2a3a', '#2471A3'),
        ]
        tk.Frame(body, bg='#0d0d1a', height=6).pack()
        for icon, title, subtitle, bg, hover in MENU:
            self._settings_card(body, icon, title, subtitle, bg, hover)

        # Logout
        tk.Frame(body, bg='#1a1a3e', height=1).pack(fill=tk.X, padx=14, pady=6)
        self._settings_card(body, "🚪", "Logout", "Sign out of your account",
                             '#3a0a0a', '#C0392B', is_logout=True)
        tk.Label(body, text="Smart Attendance System  v1.0",
                 font=("Roboto", 8), bg='#0d0d1a', fg='#333355').pack(pady=8)

    def _settings_card(self, parent, icon, title, subtitle,
                        bg, hover, is_logout=False):
        row = tk.Frame(parent, bg=bg, height=62, cursor='hand2')
        row.pack(fill=tk.X, padx=14, pady=4)
        row.pack_propagate(False)
        # Accent bar
        tk.Frame(row, bg=hover, width=4).pack(side=tk.LEFT, fill=tk.Y)
        # Icon
        tk.Label(row, text=icon, font=("Roboto", 18),
                 bg=bg, fg=hover, width=3).pack(side=tk.LEFT, padx=(6,2))
        # Text
        txt = tk.Frame(row, bg=bg)
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=10)
        tk.Label(txt, text=title,
                 font=("Inter 18pt", 10, "bold"),
                 bg=bg, fg='white', anchor='w').pack(anchor='w')
        tk.Label(txt, text=subtitle,
                 font=("Roboto", 8),
                 bg=bg, fg='#8899aa', anchor='w').pack(anchor='w')
        # Arrow
        tk.Label(row, text="›", font=("Roboto", 18),
                 bg=bg, fg=hover).pack(side=tk.RIGHT, padx=10)

        def _enter(e, r=row, h=hover):
            r.config(bg=h)
            for w in r.winfo_children():
                try: w.config(bg=h)
                except: pass
                for ww in getattr(w, 'winfo_children', lambda: [])():
                    try: ww.config(bg=h)
                    except: pass

        def _leave(e, r=row, b=bg):
            r.config(bg=b)
            for w in r.winfo_children():
                try: w.config(bg=b)
                except: pass
                for ww in getattr(w, 'winfo_children', lambda: [])():
                    try: ww.config(bg=b)
                    except: pass

        def _click(e, t=title, lgt=is_logout):
            if lgt:
                self._close_settings_panel()
                self._logout()
            else:
                # Open full settings panel on that sub-page
                self._close_settings_panel()
                sp = SettingsPanel(self.root,
                                   on_logout=self._logout,
                                   admin_name=self.admin_name)
                # Navigate to the clicked sub-page
                nav_map = {
                    "My Account":         sp._show_account,
                    "Face Recognition":   sp._show_face,
                    "Fingerprint":        sp._show_fingerprint,
                    "Display & Appearance": sp._show_themes,
                    "Privacy & Security": sp._show_privacy,
                    "Help & Support":     sp._show_about,
                }
                if t in nav_map:
                    nav_map[t]()

        row.bind('<Enter>', _enter)
        row.bind('<Leave>', _leave)
        row.bind('<Button-1>', _click)
        for child in row.winfo_children():
            child.bind('<Enter>', _enter)
            child.bind('<Leave>', _leave)
            child.bind('<Button-1>', _click)
            for gc in child.winfo_children():
                gc.bind('<Button-1>', _click)

    def _close_settings_panel(self):
        self._settings_visible = False
        if hasattr(self, '_settings_panel') and self._settings_panel:
            try: self._settings_panel.destroy()
            except: pass
            self._settings_panel = None

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            fp_session.reset()
            self.root.destroy()
            from auth import AuthWindow
            from main import launch_main_app
            auth = AuthWindow(on_login_success=launch_main_app)
            auth.run()

    def _on_close(self):
        if messagebox.askokcancel("Quit", "Exit the application?"):
            self.db.close()
            self.root.destroy()

    def run(self):
        self.root.mainloop()