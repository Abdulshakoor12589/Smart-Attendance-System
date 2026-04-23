# auth.py - With gradient buttons and form
import tkinter as tk
from tkinter import messagebox
import re
import os
import sys
from database import Database
from PIL import Image, ImageTk, ImageFilter, ImageEnhance
from gradient import GradientButton
import theme as TM
import fonts as F


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



class AuthWindow:
    def __init__(self, on_login_success):
        self.window = tk.Tk()
        self.window.title("Smart Attendance System")
        self.window.resizable(False, False)
        F.setup()

        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        self.W = 500
        self.H = min(700, sh - 60)
        self.window.geometry(
            f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}")

        self.db = Database()
        self.on_login_success = on_login_success
        self._refs = {}

        self._set_favicon()
        self._build_ui()
        self._show('signin')

    def _img(self, filename, size):
        path = os.path.join(get_base_dir(), filename)
        if not os.path.exists(path):
            return None
        try:
            photo = ImageTk.PhotoImage(
                Image.open(path).convert("RGBA").resize(
                    size, Image.Resampling.LANCZOS))
            self._refs[filename] = photo
            return photo
        except:
            return None

    def _set_favicon(self):
        ico = self._img("favicon.png", (32, 32))
        if ico:
            self.window.iconphoto(True, ico)

    def _load_bg(self):
        for name in ["14722.jpg", "14722.JPG"]:
            path = os.path.join(get_base_dir(), name)
            if os.path.exists(path):
                img = Image.open(path).resize(
                    (self.W, self.H), Image.Resampling.LANCZOS)
                img = ImageEnhance.Brightness(img).enhance(0.35)
                img = img.filter(ImageFilter.GaussianBlur(3))
                photo = ImageTk.PhotoImage(img)
                self._refs['bg'] = photo
                self.canvas.create_image(0, 0, image=photo, anchor='nw')
                return
        self.canvas.configure(bg='#2C3E50')

    def _build_ui(self):
        self.canvas = tk.Canvas(self.window, width=self.W, height=self.H,
                                highlightthickness=0)
        self.canvas.place(x=0, y=0)
        self._load_bg()

        # Icon on canvas
        icon = self._img("favicon.png", (85, 85))
        if icon:
            self.canvas.create_image(self.W // 2, 55,
                                      image=icon, anchor='center')

        # Project name
        self.canvas.create_text(self.W // 2, 108,
            text="SMART ATTENDANCE SYSTEM",
            font=("Inter 18pt", 14, "bold"), fill='#00E5CC')
        self.canvas.create_text(self.W // 2, 128,
            text="Efficient. Secure. Automated.",
            font=("Roboto", 9, "italic"), fill='#7ecdc4')

        # Gradient tab buttons
        tab_y = 155
        self.t_in = GradientButton(
            self.window,
            text="  SIGN IN  ",
            color1=TM.get('card1_g1','#1a6b3a'), color2=TM.get('card1_g2','#0d4a5a'),
            hover_color1=TM.get('accent','#27ae60'), hover_color2=TM.get('accent2','#0a8a7a'),
            font=("Inter 18pt", 10, "bold"),
            width=100, height=32,
            command=lambda: self._show('signin'))
        self.t_in.place(x=self.W // 2 - 110, y=tab_y)

        self.t_up = GradientButton(
            self.window,
            text="  SIGN UP  ",
            color1=TM.get('panel','#2a2a2a'), color2=TM.get('entry_bg','#1a1a2e'),
            hover_color1=TM.get('card2_g1','#1a3a6b'), hover_color2=TM.get('card2_g2','#0d2a5a'),
            font=("Inter 18pt", 10, "bold"),
            width=100, height=32,
            command=lambda: self._show('signup'))
        self.t_up.place(x=self.W // 2 + 10, y=tab_y)

        # Form frame
        self.form = tk.Frame(self.window, bg=TM.get('bg','#0d0d1a'))
        self.form.place(x=30, y=tab_y + 45, width=self.W - 60)

    def _show(self, mode):
        if mode == 'signup' and self.db.get_admin_count() >= 2:
            messagebox.showerror("Limit Reached",
                "Maximum 2 admin accounts exist.\nPlease sign in.")
            return
        self.mode = mode
        # Update tab colors
        if mode == 'signin':
            self.t_in.color1 = TM.get('card1_g1','#1a6b3a'); self.t_in.color2 = TM.get('card1_g2','#0d4a5a')
            self.t_up.color1 = TM.get('panel','#2a2a2a'); self.t_up.color2 = TM.get('entry_bg','#1a1a2e')
        else:
            self.t_in.color1 = TM.get('panel','#2a2a2a'); self.t_in.color2 = TM.get('entry_bg','#1a1a2e')
            self.t_up.color1 = TM.get('card2_g1','#1a3a6b'); self.t_up.color2 = TM.get('card2_g2','#0d2a5a')
        self.t_in._draw(); self.t_up._draw()

        for w in self.form.winfo_children():
            w.destroy()
        if mode == 'signin':
            self._signin_form()
        else:
            self._signup_form()

    def _signin_form(self):
        f, BG, PX = self.form, TM.get('bg','#0d0d1a'), 20

        tk.Label(f, text="Welcome Back!",
                 font=("Inter 18pt", 15, "bold"),
                 bg=BG, fg='white').pack(pady=(16, 4))

        if self.db.get_admin_count() == 0:
            tk.Label(f, text="⚠  No admins yet — please Sign Up first",
                     font=("Roboto", 9), bg='#856404', fg='#FFF3CD',
                     pady=4).pack(fill=tk.X, padx=PX, pady=(0, 6))

        self._lbl(f, "Admin Name", BG)
        self.e_user = self._entry(f, "Enter your admin name")

        self._lbl(f, "Password", BG)
        self.e_pass = self._entry(f, "Enter your password", show="*")

        self.e_user.bind('<Return>', lambda e: self.e_pass.focus_set())
        self.e_pass.bind('<Return>', lambda e: self._do_signin())

        tk.Frame(f, bg=BG, height=14).pack()

        # Gradient sign in button
        btn_frame = tk.Frame(f, bg=BG)
        btn_frame.pack(fill=tk.X, padx=PX)
        sign_btn = GradientButton(
            btn_frame, text="SIGN IN",
            color1=TM.get('card1_g1','#1a6b3a'), color2=TM.get('card1_g2','#0d4a5a'),
            hover_color1=TM.get('accent','#27ae60'), hover_color2=TM.get('accent2','#0a8a7a'),
            font=("Inter 18pt", 12, "bold"),
            height=42, command=self._do_signin)
        sign_btn.pack(fill=tk.X)

        tk.Frame(f, bg=BG, height=16).pack()

    def _do_signin(self):
        u = self.e_user.get_real().strip()
        p = self.e_pass.get_real()
        if not u or not p:
            messagebox.showerror("Error", "Please fill in all fields."); return
        if self.db.verify_admin(u, p):
            self.window.destroy()
            self.on_login_success(u)
        else:
            messagebox.showerror("Error", "Invalid admin name or password.")

    def _signup_form(self):
        f, BG, PX = self.form, TM.get('bg','#0d0d1a'), 20

        tk.Frame(f, bg=BG, height=10).pack()
        tk.Label(f, text="Create Admin Account",
                 font=("Inter 18pt", 14, "bold"),
                 bg=BG, fg='white').pack()
        tk.Label(f, text=f"Slots used: {self.db.get_admin_count()} / 2",
                 font=("Roboto", 9), bg=BG, fg=TM.get('accent','#00E5CC')).pack(pady=(2, 6))

        self._lbl(f, "Admin Name *", BG)
        self.e_name = self._entry(f, "Enter admin name")

        self._lbl(f, "Phone Number *", BG)
        self.e_phone = self._entry(f, "10–15 digit phone number")

        self._lbl(f, "Password *  (min 6 chars)", BG)
        self.e_np = self._entry(f, "Create a password", show="*")

        self._lbl(f, "Confirm Password *", BG)
        self.e_cp = self._entry(f, "Re-enter your password", show="*")

        self.e_name.bind('<Return>',  lambda e: self.e_phone.focus_set())
        self.e_phone.bind('<Return>', lambda e: self.e_np.focus_set())
        self.e_np.bind('<Return>',    lambda e: self.e_cp.focus_set())
        self.e_cp.bind('<Return>',    lambda e: self._do_signup())

        tk.Frame(f, bg=BG, height=10).pack()

        btn_frame = tk.Frame(f, bg=BG)
        btn_frame.pack(fill=tk.X, padx=PX)
        create_btn = GradientButton(
            btn_frame, text="CREATE ACCOUNT",
            color1=TM.get('card2_g1','#1a3a6b'), color2=TM.get('card2_g2','#0d2a5a'),
            hover_color1=TM.get('accent','#2980B9'), hover_color2=TM.get('accent2','#1a5a9a'),
            font=("Inter 18pt", 12, "bold"),
            height=42, command=self._do_signup)
        create_btn.pack(fill=tk.X)
        tk.Frame(f, bg=BG, height=14).pack()

    def _do_signup(self):
        name  = self.e_name.get_real().strip()
        phone = self.e_phone.get_real().strip()
        pw    = self.e_np.get_real()
        cpw   = self.e_cp.get_real()

        if not all([name, phone, pw, cpw]):
            messagebox.showerror("Error", "Please fill in all fields."); return
        if len(pw) < 6:
            messagebox.showerror("Error", "Min 6 character password required."); return
        if pw != cpw:
            messagebox.showerror("Error", "Passwords do not match."); return
        if not re.match(r'^\d{10,15}$', phone):
            messagebox.showerror("Error", "Phone must be 10–15 digits only."); return

        ok, msg = self.db.add_admin(name, phone, pw)
        if ok:
            messagebox.showinfo("Success",
                f"Account created for '{name}'!\nPlease sign in.")
            self._show('signin')
        else:
            messagebox.showerror("Error", msg)

    def _lbl(self, parent, text, bg):
        tk.Label(parent, text=text, font=("Roboto", 9, "bold"),
                 bg=bg, fg='#aaaaaa').pack(anchor='w', pady=(8, 1), padx=20)

    def _entry(self, parent, placeholder, show=None):
        e = tk.Entry(parent, font=("Roboto", 11),
                     bg=TM.get('entry_bg','#1e1e2e'), fg='#aaaaaa',
                     insertbackground='white',
                     relief=tk.FLAT,
                     highlightthickness=1,
                     highlightbackground='#333',
                     highlightcolor=TM.get('accent','#00E5CC'),
                     show='')
        e.pack(fill=tk.X, ipady=7, padx=20, pady=(1, 0))
        e._placeholder = placeholder
        e._show = show or ''
        e._active = False
        e.insert(0, placeholder)

        def on_in(ev):
            if not e._active:
                e.delete(0, tk.END)
                e.config(fg='white', show=e._show)
                e._active = True

        def on_out(ev):
            if e.get() == '':
                e.config(show='', fg='#aaaaaa')
                e.insert(0, placeholder)
                e._active = False

        e.bind('<FocusIn>',  on_in)
        e.bind('<FocusOut>', on_out)
        e.get_real = lambda: '' if not e._active else e.get()
        return e

    def run(self):
        self.window.mainloop()