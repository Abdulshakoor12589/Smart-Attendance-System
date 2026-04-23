# settings.py - Settings with navigation (main menu → sub-pages)
import tkinter as tk
from tkinter import messagebox
import os, sys, json
from PIL import Image, ImageTk, ImageFilter, ImageEnhance
from database import Database
from gradient import GradientFrame, GradientButton


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_writable_dir():
    """For saving files like settings and database — next to the .exe"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


SETTINGS_FILE = os.path.join(get_writable_dir(), "app_settings.json")


def load_settings():
    defaults = {"camera_index": 0, "face_tolerance": 0.5, "admin_name": "", "time_format": "24h"}
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE) as f:
                defaults.update(json.load(f))
    except: pass
    return defaults


def save_settings(data):
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[settings] save error: {e}")


# ─────────────────────────────────────────────────────────────────────────────

class SettingsPanel:
    def __init__(self, parent, on_logout=None, admin_name="Admin"):
        self.parent     = parent
        self.on_logout  = on_logout
        self.admin_name = admin_name
        self.db         = Database()
        self.settings   = load_settings()

        self.win = tk.Toplevel(parent)
        self.win.title("Settings")
        self.win.resizable(False, False)
        self.win.transient(parent)

        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        W, H = 460, 620
        self.win.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        self.W, self.H = W, H

        self._set_icon()
        self._show_main()
        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)

    def _set_icon(self):
        for name in ["favicon.png", "favicon.ico"]:
            path = os.path.join(get_base_dir(), name)
            if os.path.exists(path):
                try:
                    img = tk.PhotoImage(file=path)
                    self.win.iconphoto(False, img)
                    self._icon = img
                except: pass
                break

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _clear(self):
        for w in self.win.winfo_children():
            w.destroy()

    def _header(self, title, back=False):
        hdr = GradientFrame(self.win, '#0d0d2e', '#001a1a', height=58)
        hdr.place(x=0, y=0, relwidth=1)
        def dh(e, h=hdr, t=title, b=back):
            h._on_resize(e); h.delete('w')
            h.create_text(e.width//2, 29,
                text=t, font=("Inter 18pt", 15, "bold"),
                fill='#00E5CC', tags='w')
            if b:
                h.create_text(22, 29, text="←",
                    font=("Inter 18pt", 16, "bold"),
                    fill='#00E5CC', tags='w', anchor='w')
        hdr.bind('<Configure>', dh)
        if back:
            hdr.bind('<Button-1>', lambda e: self._show_main())
            hdr.config(cursor='hand2')
        tk.Frame(self.win, bg='#00E5CC', height=2).place(x=0, y=58, relwidth=1)
        return hdr

    def _scrollable_body(self, y_start=60):
        outer = tk.Frame(self.win, bg='#0d0d1a')
        outer.place(x=0, y=y_start, relwidth=1, relheight=1, height=-y_start)

        canvas = tk.Canvas(outer, bg='#0d0d1a',
                            highlightthickness=0, bd=0)
        sb = tk.Scrollbar(outer, orient=tk.VERTICAL,
                           command=canvas.yview,
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
        return body

    def _section_lbl(self, parent, text):
        f = tk.Frame(parent, bg='#0d1a2e', height=34)
        f.pack(fill=tk.X, pady=(10, 0))
        f.pack_propagate(False)
        tk.Label(f, text=text, font=("Inter 18pt", 10, "bold"),
                 bg='#0d1a2e', fg='#00E5CC').pack(side=tk.LEFT, padx=16, pady=6)

    def _info_row(self, parent, label, value):
        f = tk.Frame(parent, bg='#111128', height=40)
        f.pack(fill=tk.X, padx=18, pady=2)
        f.pack_propagate(False)
        tk.Label(f, text=label + ":", font=("Roboto", 9, "bold"),
                 bg='#111128', fg='#7ecdc4', width=18, anchor='w').pack(
                     side=tk.LEFT, padx=14)
        tk.Label(f, text=value, font=("Roboto", 9),
                 bg='#111128', fg='#cccccc').pack(side=tk.LEFT)

    def _entry(self, parent, label, show=None):
        tk.Label(parent, text=label, font=("Inter 18pt", 9, "bold"),
                 bg='#0d0d1a', fg='#00E5CC').pack(
                     anchor='w', padx=18, pady=(10, 1))
        e = tk.Entry(parent, font=("Roboto", 10),
                     bg='#1a1a2e', fg='white',
                     insertbackground='white', relief=tk.FLAT,
                     highlightthickness=1,
                     highlightbackground='#2a2a4e',
                     highlightcolor='#00E5CC',
                     show=show or '')
        e.pack(fill=tk.X, padx=18, ipady=6)
        return e

    def _action_btn(self, parent, text, c1, c2, cmd, height=40):
        f = tk.Frame(parent, bg='#0d0d1a')
        f.pack(fill=tk.X, padx=18, pady=4)
        GradientButton(f, text=text,
            color1=c1, color2=c1,
            hover_color1=c2, hover_color2=c2,
            font=("Inter 18pt", 10, "bold"),
            height=height, command=cmd).pack(fill=tk.X)

    def _msg_label(self, parent):
        lbl = tk.Label(parent, text="", font=("Roboto", 9),
                       bg='#0d0d1a', fg='#e74c3c', wraplength=400)
        lbl.pack(padx=18, pady=2)
        return lbl

    # ══════════════════════════════════════════════════════════════════════════
    # MAIN MENU
    # ══════════════════════════════════════════════════════════════════════════

    def _show_main(self):
        self._clear()
        self._header("⚙   SETTINGS")
        body = self._scrollable_body(60)

        MENU = [
            ("👤", "My Account",
             "Change password, view profile",
             '#1a2a4a', '#2980B9', self._show_account),

            ("🎯", "Face Recognition",
             "Camera settings & sensitivity",
             '#1a3a1a', '#27ae60', self._show_face),

            ("👆", "Fingerprint",
             "Windows Hello & USB scanner settings",
             '#2a1a4a', '#7D3C98', self._show_fingerprint),

            ("🔒", "Privacy & Security",
             "Data storage & backup",
             '#2a1a3a', '#7D3C98', self._show_privacy),

            ("🎨", "Display & Appearance",
             "Themes & color palettes",
             '#2a1a0a', '#E67E22', self._show_themes),

            ("❓", "Help & Support",
             "About & system information",
             '#1a2a3a', '#2471A3', self._show_about),

            ("🚪", "Logout",
             "Sign out of your account",
             '#3a0a0a', '#C0392B', self._do_logout),
        ]

        tk.Frame(body, bg='#0d0d1a', height=8).pack()

        for icon, title, subtitle, bg, hover, cmd in MENU:
            row = tk.Frame(body, bg=bg, height=72, cursor='hand2')
            row.pack(fill=tk.X, padx=18, pady=5)
            row.pack_propagate(False)

            tk.Frame(row, bg=hover, width=5).pack(side=tk.LEFT, fill=tk.Y)

            tk.Label(row, text=icon, font=("Roboto", 22),
                     bg=bg, fg=hover, width=3).pack(side=tk.LEFT, padx=(10,4))

            txt = tk.Frame(row, bg=bg)
            txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=12)
            tk.Label(txt, text=title, font=("Inter 18pt", 11, "bold"),
                     bg=bg, fg='white', anchor='w').pack(anchor='w')
            tk.Label(txt, text=subtitle, font=("Roboto", 9),
                     bg=bg, fg='#8899aa', anchor='w').pack(anchor='w')

            tk.Label(row, text="›", font=("Roboto", 22),
                     bg=bg, fg=hover).pack(side=tk.RIGHT, padx=16)

            def _enter(e, r=row, h=hover, b=bg):
                r.config(bg=h)
                for w in r.winfo_children():
                    try: w.config(bg=h)
                    except: pass
                    for ww in w.winfo_children():
                        try: ww.config(bg=h)
                        except: pass

            def _leave(e, r=row, h=hover, b=bg):
                r.config(bg=b)
                for w in r.winfo_children():
                    try: w.config(bg=b)
                    except: pass
                    for ww in w.winfo_children():
                        try: ww.config(bg=b)
                        except: pass

            row.bind('<Enter>', _enter)
            row.bind('<Leave>', _leave)
            row.bind('<Button-1>', lambda e, c=cmd: c())
            for child in row.winfo_children():
                child.bind('<Button-1>', lambda e, c=cmd: c())
                for gc in child.winfo_children():
                    gc.bind('<Button-1>', lambda e, c=cmd: c())

        tk.Label(body, text="Smart Attendance System  v1.0",
                 font=("Roboto", 8), bg='#0d0d1a', fg='#333355').pack(pady=12)

    # ══════════════════════════════════════════════════════════════════════════
    # MY ACCOUNT
    # ══════════════════════════════════════════════════════════════════════════

    def _show_account(self):
        self._clear()
        self._header("👤  My Account", back=True)
        body = self._scrollable_body(60)

        self._section_lbl(body, "Profile")
        self._info_row(body, "Username",  self.admin_name)
        self._info_row(body, "Role",      "Administrator")
        self._info_row(body, "Access",    "Full access")

        self._section_lbl(body, "Change Password")

        self.e_old = self._entry(body, "Current Password:", show='●')
        self.e_new = self._entry(body, "New Password:",     show='●')
        self.e_cnf = self._entry(body, "Confirm Password:", show='●')

        self.e_old.bind('<Return>', lambda e: self.e_new.focus_set())
        self.e_new.bind('<Return>', lambda e: self.e_cnf.focus_set())
        self.e_cnf.bind('<Return>', lambda e: self._do_change_password())

        self._pw_msg = self._msg_label(body)

        self._action_btn(body, "💾  Save New Password",
                         '#1a5a1a', '#27ae60', self._do_change_password, 44)
        self._action_btn(body, "← Back to Settings",
                         '#1a1a3e', '#2a2a5e', self._show_main)

    def _do_change_password(self):
        old_p = self.e_old.get().strip()
        new_p = self.e_new.get().strip()
        cnf_p = self.e_cnf.get().strip()
        if not all([old_p, new_p, cnf_p]):
            self._pw_msg.config(text="⚠  Fill all fields.", fg='#e74c3c'); return
        if new_p != cnf_p:
            self._pw_msg.config(text="⚠  Passwords don't match.", fg='#e74c3c'); return
        if len(new_p) < 6:
            self._pw_msg.config(text="⚠  Min 6 characters.", fg='#e74c3c'); return
        ok, err = self.db.change_admin_password(self.admin_name, old_p, new_p)
        if ok:
            self._pw_msg.config(text="✅  Password changed!", fg='#27ae60')
            self.win.after(1500, self._show_main)
        else:
            self._pw_msg.config(text=f"❌  {err or 'Incorrect password.'}", fg='#e74c3c')

    # ══════════════════════════════════════════════════════════════════════════
    # FACE RECOGNITION
    # ══════════════════════════════════════════════════════════════════════════

    def _show_face(self):
        self._clear()
        self._header("🎯  Face Recognition", back=True)
        body = self._scrollable_body(60)

        self._section_lbl(body, "Camera Selection")
        self._info_row(body, "Current",
                       f"Camera {self.settings['camera_index']}")

        cam_f = tk.Frame(body, bg='#111128')
        cam_f.pack(fill=tk.X, padx=18, pady=4)
        tk.Label(cam_f, text="Select camera:",
                 font=("Roboto", 10), bg='#111128',
                 fg='#7ecdc4').pack(anchor='w', padx=14, pady=(8,2))

        self.cam_var = tk.IntVar(value=self.settings['camera_index'])
        for idx, lbl in enumerate(["0 — Built-in / default camera",
                                    "1 — USB Camera 1",
                                    "2 — USB Camera 2"]):
            tk.Radiobutton(cam_f, text=lbl, variable=self.cam_var, value=idx,
                           font=("Roboto", 10), bg='#111128', fg='white',
                           selectcolor='#0d0d2e', activebackground='#111128',
                           activeforeground='#00E5CC').pack(
                               anchor='w', padx=24, pady=3)
        tk.Frame(cam_f, bg='#0d0d1a', height=8).pack()

        self._section_lbl(body, "Recognition Sensitivity")
        tol_f = tk.Frame(body, bg='#111128')
        tol_f.pack(fill=tk.X, padx=18, pady=4)

        tk.Label(tol_f, text="Lower = stricter (fewer false positives)\n"
                             "Higher = looser (fewer missed detections)",
                 font=("Roboto", 9), bg='#111128', fg='#8899aa',
                 justify=tk.LEFT).pack(anchor='w', padx=14, pady=(8,4))

        sl_row = tk.Frame(tol_f, bg='#111128')
        sl_row.pack(fill=tk.X, padx=14, pady=(0,10))
        tk.Label(sl_row, text="Strict\n0.3", font=("Roboto", 8),
                 bg='#111128', fg='#7ecdc4').pack(side=tk.LEFT)
        self.tol_var = tk.DoubleVar(value=self.settings['face_tolerance'])
        tk.Scale(sl_row, variable=self.tol_var,
                 from_=0.3, to=0.7, resolution=0.05,
                 orient=tk.HORIZONTAL, length=280,
                 bg='#111128', fg='#00E5CC',
                 troughcolor='#1a1a2e', highlightthickness=0,
                 font=("Roboto", 8)).pack(side=tk.LEFT, padx=6)
        tk.Label(sl_row, text="Loose\n0.7", font=("Roboto", 8),
                 bg='#111128', fg='#7ecdc4').pack(side=tk.LEFT)

        self._section_lbl(body, "Clock Format")
        tf_f = tk.Frame(body, bg='#111128')
        tf_f.pack(fill=tk.X, padx=18, pady=4)
        tk.Label(tf_f, text="Select time format used across the system:",
                 font=("Roboto", 9), bg='#111128',
                 fg='#8899aa').pack(anchor='w', padx=14, pady=(8,4))
        self.time_fmt_var = tk.StringVar(
            value=self.settings.get('time_format', '24h'))
        for val, lbl in [('12h', '🕐  12-Hour  (e.g. 02:30 PM)'),
                          ('24h', '🕐  24-Hour  (e.g. 14:30)')]:
            tk.Radiobutton(tf_f, text=lbl,
                           variable=self.time_fmt_var, value=val,
                           font=("Roboto", 10),
                           bg='#111128', fg='white',
                           selectcolor='#0d0d2e',
                           activebackground='#111128',
                           activeforeground='#00E5CC').pack(
                               anchor='w', padx=24, pady=4)
        tk.Frame(tf_f, bg='#0d0d1a', height=8).pack()

        self._fr_msg = self._msg_label(body)
        self._action_btn(body, "💾  Save Settings",
                         '#1a5a1a', '#27ae60', self._save_face, 44)
        self._action_btn(body, "← Back to Settings",
                         '#1a1a3e', '#2a2a5e', self._show_main)

    def _save_face(self):
        self.settings['camera_index']   = self.cam_var.get()
        self.settings['face_tolerance'] = round(self.tol_var.get(), 2)
        self.settings['time_format']    = self.time_fmt_var.get()
        save_settings(self.settings)
        self._fr_msg.config(
            text=f"✅  Saved! Camera {self.settings['camera_index']}, "
                 f"Sensitivity {self.settings['face_tolerance']}",
            fg='#27ae60')
        self.win.after(1500, self._show_main)

    # ══════════════════════════════════════════════════════════════════════════
    # FINGERPRINT
    # ══════════════════════════════════════════════════════════════════════════

    def _show_fingerprint(self):
        self._clear()
        self._header("👆  Fingerprint Scanner", back=True)
        body = self._scrollable_body(60)

        cur = self.settings.get('fp_device', 'none')
        self._section_lbl(body, "Current Device")
        if cur == 'none':
            tk.Label(body, text="⛔  No scanner selected — fingerprint disabled",
                     font=("Inter 18pt", 10, "bold"),
                     bg='#0d0d1a', fg='#e74c3c').pack(anchor='w', padx=22, pady=8)
        else:
            tk.Label(body, text=f"🔌  {cur.replace('_',' ').title()} selected",
                     font=("Inter 18pt", 10, "bold"),
                     bg='#0d0d1a', fg='#27ae60').pack(anchor='w', padx=22, pady=8)

        self._section_lbl(body, "USB Fingerprint Scanner")
        usb_f = tk.Frame(body, bg='#111128')
        usb_f.pack(fill=tk.X, padx=18, pady=4)
        tk.Label(usb_f,
                 text="Select USB port your scanner is connected to:",
                 font=("Roboto", 9), bg='#111128',
                 fg='#8899aa').pack(anchor='w', padx=14, pady=(10,4))
        self.fp_device_var = tk.StringVar(value=cur)
        for val, lbl in [
            ('usb_1', '🔌  USB Port 1  (ZKTeco ZK4500 / ZK9500)'),
            ('usb_2', '🔌  USB Port 2'),
            ('none',  '⛔  None — fingerprint disabled'),
        ]:
            tk.Radiobutton(usb_f, text=lbl,
                variable=self.fp_device_var, value=val,
                font=("Roboto", 10), bg='#111128',
                fg='#e74c3c' if val=='none' else 'white',
                selectcolor='#0d0d2e',
                activebackground='#111128',
                activeforeground='#00E5CC').pack(anchor='w', padx=24, pady=4)
        tk.Frame(usb_f, bg='#0d0d1a', height=6).pack()

        notice = tk.Frame(body, bg='#1a1400', highlightthickness=1,
                          highlightbackground='#f39c12')
        notice.pack(fill=tk.X, padx=18, pady=10)
        tk.Label(notice,
                 text="Fingerprint Only and Both options are hidden\n"
                      "until a USB scanner is selected and connected.",
                 font=("Roboto", 9), bg='#1a1400', fg='#f39c12',
                 justify=tk.CENTER).pack(pady=10)

        self._section_lbl(body, "How to Set Up")
        for s in [
            "1.  Buy ZKTeco ZK4500 (~Rs. 3,500 on Daraz.pk)",
            "2.  Install ZKFinger SDK from zkteco.com",
            "3.  Plug scanner into USB port",
            "4.  Select port above → Save → restart app",
            "5.  Fingerprint options will appear automatically",
        ]:
            tk.Label(body, text=s, font=("Roboto", 9),
                     bg='#0d0d1a', fg='#8899aa',
                     anchor='w').pack(anchor='w', padx=22, pady=2)

        self._fp_msg = self._msg_label(body)
        self._action_btn(body, "💾  Save Scanner Setting",
                         '#4a1a6b', '#7D3C98', self._save_fingerprint, 44)
        self._action_btn(body, "← Back to Settings",
                         '#1a1a3e', '#2a2a5e', self._show_main)

    def _save_fingerprint(self):
        self.settings['fp_device'] = self.fp_device_var.get()
        # fp_prompt_var only exists in old method — guard against AttributeError
        if hasattr(self, 'fp_prompt_var'):
            self.settings['fp_prompt'] = self.fp_prompt_var.get().strip() or \
                                         'Please verify your identity'
        save_settings(self.settings)
        device_labels = {
            'usb_1': 'USB Scanner — Port 1',
            'usb_2': 'USB Scanner — Port 2',
            'none':  'Disabled',
        }
        self._fp_msg.config(
            text=f"✅  Saved! Device: {device_labels.get(self.settings['fp_device'], 'Unknown')}",
            fg='#27ae60')
        self.win.after(1500, self._show_main)

    # ══════════════════════════════════════════════════════════════════════════
    # PRIVACY & SECURITY
    # ══════════════════════════════════════════════════════════════════════════

    def _show_privacy(self):
        self._clear()
        self._header("🔒  Privacy & Security", back=True)
        body = self._scrollable_body(60)

        self._section_lbl(body, "Data Storage")
        self._info_row(body, "Database",    "smart_attendance.db")
        self._info_row(body, "Location",    "App install folder (writable)")
        self._info_row(body, "Face Images", "/students/ folder (local)")
        self._info_row(body, "Fingerprint", "Windows Hello — no raw data stored")
        self._info_row(body, "Passwords",   "SHA-256 hashed, never plain text")

        self._section_lbl(body, "Database Backup")
        tk.Label(body,
                 text="Create a backup copy of your database to prevent data loss.",
                 font=("Roboto", 9), bg='#0d0d1a', fg='#8899aa',
                 wraplength=400).pack(anchor='w', padx=18, pady=(6,2))
        self._action_btn(body, "🗄  Backup Database Now",
                         '#1a3a6b', '#2980B9', self._backup_db, 44)

        self._section_lbl(body, "Data Management")
        tk.Label(body,
                 text="⚠  Deleting data is permanent and cannot be undone.",
                 font=("Roboto", 9), bg='#0d0d1a', fg='#e67e22',
                 wraplength=400).pack(anchor='w', padx=18, pady=(6,2))
        self._action_btn(body, "🗑  Delete All Attendance Records",
                         '#3a1a00', '#E67E22', self._delete_attendance, 40)

        self._action_btn(body, "← Back to Settings",
                         '#1a1a3e', '#2a2a5e', self._show_main)

    def _backup_db(self):
        import shutil
        from tkinter import filedialog
        src = os.path.join(get_writable_dir(), "smart_attendance.db")
        if not os.path.exists(src):
            messagebox.showerror("Error", "Database not found!"); return
        dst = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All files", "*.*")],
            initialfile="smart_attendance_backup.db",
            title="Save Backup")
        if dst:
            shutil.copy2(src, dst)
            messagebox.showinfo("✅ Backup Saved",
                f"Database backed up to:\n{dst}")

    def _delete_attendance(self):
        if not messagebox.askyesno("⚠  Confirm Delete",
            "Delete ALL attendance records?\n\n"
            "Students will NOT be deleted.\n"
            "This cannot be undone!"):
            return
        try:
            self.db.cursor.execute("DELETE FROM attendance")
            self.db.conn.commit()
            messagebox.showinfo("✅ Done",
                "All attendance records deleted.\nStudents are still registered.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ══════════════════════════════════════════════════════════════════════════
    # DISPLAY & APPEARANCE
    # ══════════════════════════════════════════════════════════════════════════

    def _show_themes(self):
        self._clear()
        self._header("🎨  Display & Appearance", back=True)
        body = self._scrollable_body(60)
        import theme as TM
        self._theme_var = tk.StringVar(value=TM.name())

        self._section_lbl(body, "Choose Theme")
        tk.Label(body,
                 text="Each theme uses your color palettes as gradients",
                 font=("Roboto", 9), bg='#0d0d1a', fg='#8899aa',
                 wraplength=400).pack(anchor='w', padx=18, pady=(4,8))

        PREVIEWS = [
            ("Steel Blue",   "#020b17","#111827","#1f2937","#9ca3af",
             "Dark navy blues + silver grey"),
            ("Deep Forest",  "#000505","#101615","#1e2f2a","#8fa99a",
             "Deep black + dark forest greens"),
            ("Graphite",     "#1a1a1a","#222222","#3b3b3b","#cfcfcf",
             "Pure charcoal grey scale"),
            ("Royal Purple", "#0d0118","#1a0533","#2d0f5e","#a855f7",
             "Dark purple + violet gradients"),
            ("Coffee",       "#1c0a0a","#2a1208","#3b1a0a","#c8956c",
             "Espresso brown + caramel tones"),
        ]

        for t_name, bg, p1, p2, acc, desc in PREVIEWS:
            active  = (t_name == TM.name())
            row_bg  = p1 if active else '#111128'
            row = tk.Frame(body, bg=row_bg, cursor='hand2',
                           highlightthickness=2 if active else 0,
                           highlightbackground=acc)
            row.pack(fill=tk.X, padx=18, pady=4)

            sw = tk.Canvas(row, width=70, height=52,
                           highlightthickness=0, bg=bg)
            sw.pack(side=tk.LEFT, padx=10, pady=6)
            sw.create_rectangle(0,  0, 24, 52, fill=bg,  outline='')
            sw.create_rectangle(23, 0, 47, 52, fill=p1,  outline='')
            sw.create_rectangle(46, 0, 70, 52, fill=p2,  outline='')
            sw.create_rectangle(0, 40, 70, 52, fill=acc, outline='')

            txt = tk.Frame(row, bg=row_bg)
            txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
            tk.Label(txt, text=t_name,
                     font=("Inter 18pt", 11, "bold"),
                     bg=row_bg, fg=acc, anchor='w').pack(anchor='w')
            tk.Label(txt, text=desc, font=("Roboto", 8),
                     bg=row_bg, fg='#8899aa', anchor='w').pack(anchor='w')

            rb = tk.Radiobutton(row, variable=self._theme_var,
                value=t_name, bg=row_bg, fg=acc, selectcolor=bg,
                activebackground=row_bg, cursor='hand2',
                command=lambda n=t_name: self._theme_var.set(n))
            rb.pack(side=tk.RIGHT, padx=12)
            if active:
                tk.Label(row, text="✓ Active", font=("Roboto", 8, "bold"),
                         bg=row_bg, fg=acc).pack(side=tk.RIGHT, padx=4)

            row.bind('<Button-1>', lambda e, n=t_name: self._theme_var.set(n))
            for child in row.winfo_children():
                child.bind('<Button-1>', lambda e, n=t_name: self._theme_var.set(n))

        self._theme_msg = self._msg_label(body)
        self._action_btn(body, "💾  Apply Selected Theme",
                         '#1a5a1a', '#27ae60', self._apply_theme, 46)
        self._action_btn(body, "← Back to Settings",
                         '#1a1a3e', '#2a2a5e', self._show_main)

    def _apply_theme(self):
        import theme as TM
        name = self._theme_var.get()
        TM.save(name)
        try:
            self._theme_msg.config(
                text=f"✅  '{name}' applied! Restarting app...",
                fg='#27ae60')
        except: pass
        self.win.after(1200, self._restart_app)

    def _restart_app(self):
        import sys, os, subprocess
        try:
            self.win.destroy()
        except: pass
        python = sys.executable
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        subprocess.Popen([python, script])
        sys.exit(0)

    # ══════════════════════════════════════════════════════════════════════════
    # HELP & SUPPORT
    # ══════════════════════════════════════════════════════════════════════════

    def _show_about(self):
        self._clear()
        self._header("❓  Help & Support", back=True)
        body = self._scrollable_body(60)

        self._section_lbl(body, "About This System")
        self._info_row(body, "System",    "Smart Attendance System")
        self._info_row(body, "Version",   "v1.0")
        self._info_row(body, "Platform",  "Windows 10 / 11")

        self._section_lbl(body, "Technology")
        self._info_row(body, "Language",  "Python 3.11")
        self._info_row(body, "UI",        "Tkinter")
        self._info_row(body, "Database",  "SQLite3")
        self._info_row(body, "Face AI",   "dlib + face_recognition")
        self._info_row(body, "Biometric", "Windows Hello (WinRT)")
        self._info_row(body, "Reports",   "openpyxl (Excel)")

        self._section_lbl(body, "How To Use")
        steps = [
            "1.  Register students from the dashboard",
            "2.  Choose Face, Fingerprint, or Both method",
            "3.  Open Door Attendance to mark present",
            "4.  View history in Reports section",
            "5.  Export monthly report as Excel file",
        ]
        for s in steps:
            tk.Label(body, text=s, font=("Roboto", 10),
                     bg='#0d0d1a', fg='#cccccc',
                     anchor='w').pack(anchor='w', padx=22, pady=2)

        self._section_lbl(body, "Troubleshooting")
        tips = [
            "• Face not recognized → Re-register in good lighting",
            "• Camera not opening → Check camera index in Face Recognition settings",
            "• Fingerprint not working → Run app via run.bat, not VS Code",
            "• Database locked → Restart the app",
        ]
        for t in tips:
            tk.Label(body, text=t, font=("Roboto", 9),
                     bg='#0d0d1a', fg='#8899aa',
                     anchor='w', wraplength=400).pack(
                         anchor='w', padx=22, pady=2)

        self._action_btn(body, "← Back to Settings",
                         '#1a1a3e', '#2a2a5e', self._show_main)

    # ══════════════════════════════════════════════════════════════════════════
    # LOGOUT
    # ══════════════════════════════════════════════════════════════════════════

    def _do_logout(self):
        if not messagebox.askyesno("Logout",
            "Are you sure you want to logout?"):
            return
        self.win.destroy()
        if self.on_logout:
            self.on_logout()