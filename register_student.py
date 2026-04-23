# register_student.py - Clean fixed layout
import tkinter as tk
from tkinter import ttk, messagebox
import cv2, os, sys, threading
from PIL import Image, ImageTk, ImageFilter, ImageEnhance
from database import Database
from gradient import GradientButton, GradientFrame
import theme as TM
import fp_session
from settings import load_settings


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



class RegisterStudentWindow:
    def __init__(self, parent, container=None):
        W, H = 1100, 740
        if container is not None:
            self.window = container
            self.standalone = False
        else:
            self.window = tk.Toplevel(parent)
            self.window.title("Register New Student")
            _set_app_icon(self.window)
            self.window.resizable(True, True)
            self.window.transient(parent)
            sw = self.window.winfo_screenwidth()
            sh = self.window.winfo_screenheight()
            W = min(1100, sw - 40)
            H = min(740,  sh - 40)
            self.window.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
            self.W, self.H = W, H
            self.standalone = True

        self.db             = Database()
        self.capture        = None
        self.current_frame  = None
        self.captured_frame = None
        self.camera_running = False
        self.face_captured  = False
        self.fp_verified    = False
        self.method_var     = tk.StringVar(value='face')
        self._refs          = {}

        os.makedirs("students", exist_ok=True)
        self._build_ui()
        if self.standalone: self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── background ────────────────────────────────────────────────────────────

    def _load_bg(self, w, h):
        for name in ["tb.jpg", "tb.JPG"]:
            path = os.path.join(get_base_dir(), name)
            if os.path.exists(path):
                img = Image.open(path).resize((w, h), Image.Resampling.LANCZOS)
                img = ImageEnhance.Brightness(img).enhance(0.28)
                img = img.filter(ImageFilter.GaussianBlur(4))
                photo = ImageTk.PhotoImage(img)
                self._refs['bg'] = photo
                return photo
        return None

    def _draw_bg(self):
        w = self.window.winfo_width()  or self.W
        h = self.window.winfo_height() or self.H
        p = self._load_bg(w, h)
        if p:
            self.bg_canvas.delete('bg')
            self.bg_canvas.create_image(0, 0, image=p, anchor='nw', tags='bg')
            self.bg_canvas.tag_lower('bg')

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.bg_canvas = tk.Canvas(self.window, highlightthickness=0, bd=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self.window.bind('<Configure>',
            lambda e: self._draw_bg() if e.widget is self.window else None)
        self._draw_bg()

        # Header
        hdr = GradientFrame(self.window, TM.get('header_grad1','#0d0d2e'), TM.get('header_grad2','#001a1a'), height=56)
        hdr.place(x=0, y=0, relwidth=1)
        def draw_hdr(e, h=hdr):
            h._on_resize(e); h.delete('widgets')
            h.create_text(e.width//2, 28,
                text="📝   STUDENT REGISTRATION",
                font=("Inter 18pt", 16, "bold"),
                fill='#00E5CC', tags='widgets')
        hdr.bind('<Configure>', draw_hdr)
        tk.Frame(self.window, bg='#00E5CC', height=2).place(x=0, y=56, relwidth=1)

        # Method strip
        mstrip = tk.Frame(self.window, bg='#080814', height=44)
        mstrip.place(x=0, y=58, relwidth=1)
        tk.Label(mstrip, text="Method:",
                 font=("Inter 18pt", 9, "bold"),
                 bg='#080814', fg=TM.get('accent2','#7ecdc4')).place(x=12, y=11)

        self._method_btns = {}
        # Show 'Both' option only if USB scanner configured in settings
        _fp_dev = load_settings().get('fp_device', 'none')
        _methods = [('face', "📷  Face Only", 180)]
        if _fp_dev != 'none':
            _methods.append(('both', "📷 + 👆  Both", 360))

        for val, text, x in _methods:
            b = tk.Button(mstrip, text=text,
                          font=("Inter 18pt", 9, "bold"),
                          relief=tk.FLAT, cursor='hand2',
                          padx=10, pady=3,
                          command=lambda v=val: self._set_method(v))
            b.place(x=x, y=7)
            self._method_btns[val] = b

        tk.Frame(self.window, bg='#1a1a3e', height=1).place(x=0, y=102, relwidth=1)

        # ── Left panel ────────────────────────────────────────────────────────
        LEFT_W = 300
        PAD    = 14
        FW     = LEFT_W - PAD * 2   # 272px
        PB     = '#0a0a16'          # panel bg

        self.left_panel = tk.Frame(self.window, bg=PB,
                                    bd=0, highlightthickness=0)
        self.left_panel.place(x=0, y=102, width=LEFT_W,
                               relheight=1, height=-102)

        # ── Helpers ───────────────────────────────────────────────────────────
        def lbl(text, y):
            tk.Label(self.left_panel, text=text,
                     font=("Inter 18pt", 9, "bold"),
                     bg=PB, fg=TM.get('accent','#00E5CC'),
                     bd=0, highlightthickness=0
                     ).place(x=PAD, y=y)

        def ent(ph, y):
            e = _PlaceholderEntry(self.left_panel, ph,
                font=("Roboto", 10), bg=TM.get('entry_bg','#1a1a2e'), fg='white',
                insertbackground='white', relief=tk.FLAT,
                bd=0, highlightthickness=0)
            e.place(x=PAD, y=y, width=FW, height=30)
            return e

        # ── Form fields — evenly spaced ───────────────────────────────────────
        #  label y, entry y   (entry = label+18, next label = entry+38)
        lbl("Student Name",   8);  self.e_name   = ent("Full name",          26)
        lbl("Father's Name",  72); self.e_father = ent("Father's full name",  90)
        lbl("Roll Number",   136); self.e_roll   = ent("e.g. 2021-CS-01",    154)
        lbl("Reg Number",    200); self.e_reg    = ent("e.g. 2021-BSCS-123", 218)

        self.e_name.bind('<Return>',   lambda e: self.e_father.focus())
        self.e_father.bind('<Return>', lambda e: self.e_roll.focus())
        self.e_roll.bind('<Return>',   lambda e: self.e_reg.focus())

        lbl("Semester", 264)
        self.sem_var = tk.StringVar(value="1")
        sem_om = tk.OptionMenu(self.left_panel, self.sem_var,
                               *[str(i) for i in range(1, 9)])
        sem_om.config(font=("Roboto", 10),
                      bg=TM.get('entry_bg','#1a1a2e'), fg='white',
                      activebackground='#2a2a4e', activeforeground='#00E5CC',
                      relief=tk.FLAT, bd=0, highlightthickness=0,
                      cursor='hand2')
        sem_om["menu"].config(bg=TM.get('entry_bg','#1a1a2e'), fg='white',
                              activebackground='#00E5CC',
                              activeforeground='#0d0d1a',
                              font=("Roboto", 10), bd=0)
        sem_om.place(x=PAD, y=282, width=FW, height=30)

        # Divider
        tk.Frame(self.left_panel, bg='#1a1a3e', height=1).place(
            x=PAD, y=322, width=FW)

        # ── Action buttons ────────────────────────────────────────────────────
        BH = 42   # button height
        BG = 8    # gap

        self.cam_btn = GradientButton(self.left_panel,
            text="📷  Start Camera",
            color1='#1a3a6b', color2='#0d2a5a',
            hover_color1='#2980B9', hover_color2='#1a5a9a',
            font=("Inter 18pt", 10, "bold"),
            width=FW, height=BH, command=self._toggle_camera)
        self.cam_btn.place(x=PAD, y=330)

        self.cap_btn = GradientButton(self.left_panel,
            text="🎯  Capture Face",
            color1='#6b1a1a', color2='#4a0d0d',
            hover_color1='#e74c3c', hover_color2='#c0392b',
            font=("Inter 18pt", 10, "bold"),
            width=FW, height=BH, command=self._capture_face)
        self.cap_btn.place(x=PAD, y=330 + BH + BG)
        self.cap_btn.config_state(tk.DISABLED)

        self.fp_btn = GradientButton(self.left_panel,
            text="👆  Verify Fingerprint",
            color1='#4a1a6b', color2='#2d0a5a',
            hover_color1='#7D3C98', hover_color2='#5a1a8a',
            font=("Inter 18pt", 10, "bold"),
            width=FW, height=BH, command=self._do_fingerprint)

        self.save_btn = GradientButton(self.left_panel,
            text="💾  Save Student",
            color1='#1a5a1a', color2='#0d3a0d',
            hover_color1='#27ae60', hover_color2='#1a8a4a',
            font=("Inter 18pt", 11, "bold"),
            width=FW, height=BH, command=self._save_student)
        self.save_btn.config_state(tk.DISABLED)

        self.status = tk.Label(self.left_panel,
            text="⚡  Fill form and start camera",
            font=("Roboto", 8), bg=PB, fg='#f39c12',
            wraplength=FW, justify=tk.LEFT,
            relief=tk.FLAT, bd=0, highlightthickness=0)

        # ── Right camera panel ────────────────────────────────────────────────
        self.cam_panel = tk.Frame(self.window, bg=TM.get('bg','#0a0a14'),
                                   highlightthickness=0)
        self.cam_panel.place(x=LEFT_W + 4, y=102,
                              relwidth=1, width=-(LEFT_W + 6),
                              relheight=1, height=-102)

        tk.Label(self.cam_panel, text="Camera Preview",
                 font=("Inter 18pt", 12, "bold"),
                 bg=TM.get('bg','#0a0a14'), fg='white').pack(pady=(8, 2))
        tk.Frame(self.cam_panel, bg='#00E5CC', height=1).pack(
            fill=tk.X, padx=16)

        self.cam_placeholder = tk.Label(self.cam_panel,
            text="📷\n\nCamera is off\nClick 'Start Camera' to preview",
            font=("Roboto", 13), bg=TM.get('bg','#0a0a14'), fg='#444466',
            justify=tk.CENTER)
        self.cam_placeholder.pack(expand=True, fill=tk.BOTH)

        self.camera_label = tk.Label(self.cam_panel, bg='black')

        # Fingerprint right panel
        self.fp_panel = tk.Frame(self.cam_panel, bg=TM.get('bg','#0a0a14'))
        self.fp_fingers_registered = 0
        self._fp_scanning = False

        # ── STAGE: WAIT — sensor idle, waiting for scan ───────────────────────
        self.fp_stage_wait = tk.Frame(self.fp_panel, bg=TM.get('bg','#0a0a14'))
        self.fp_sensor_idle = tk.Canvas(self.fp_stage_wait,
            width=130, height=130, bg=TM.get('bg','#0a0a14'), highlightthickness=0)
        self.fp_sensor_idle.pack(pady=(30, 6))
        tk.Label(self.fp_stage_wait, text="FINGERPRINT SENSOR",
                 font=("Inter 18pt", 13, "bold"),
                 bg=TM.get('bg','#0a0a14'), fg=TM.get('accent','#00E5CC')).pack()
        self.fp_finger_lbl = tk.Label(self.fp_stage_wait,
                 text="Fingers registered: 0 / 2",
                 font=("Roboto", 9), bg=TM.get('bg','#0a0a14'), fg='#555577')
        self.fp_finger_lbl.pack(pady=4)
        self.fp_scan_btn = GradientButton(self.fp_stage_wait,
            text="👆  Scan Finger on Sensor",
            color1='#4a1a6b', color2='#2d0a5a',
            hover_color1='#7D3C98', hover_color2='#5a1a8a',
            font=("Inter 18pt", 11, "bold"),
            height=50, command=self._scan_finger)
        self.fp_scan_btn.pack(fill=tk.X, padx=40, pady=10)

        # ── STAGE: SCAN — waiting for Hello verification ─────────────────────
        self.fp_stage_scan = tk.Frame(self.fp_panel, bg=TM.get('bg','#0a0a14'))
        tk.Label(self.fp_stage_scan, text="VERIFYING FINGERPRINT",
                 font=("Inter 18pt", 12, "bold"),
                 bg=TM.get('bg','#0a0a14'), fg='#f39c12').pack(pady=(30, 4))
        tk.Label(self.fp_stage_scan,
                 text="Complete the Windows Hello prompt",
                 font=("Roboto", 9), bg=TM.get('bg','#0a0a14'), fg='#aaaaaa').pack()
        self.fp_scan_cv = tk.Canvas(self.fp_stage_scan,
            width=160, height=160, bg=TM.get('bg','#0a0a14'), highlightthickness=0)
        self.fp_scan_cv.pack(pady=10)
        self.fp_anim_lbl = tk.Label(self.fp_stage_scan,
                 text="Waiting...", font=("Roboto", 10),
                 bg=TM.get('bg','#0a0a14'), fg='#f39c12')
        self.fp_anim_lbl.pack(pady=4)

        # ── STAGE: SUCCESS — finger scanned OK ────────────────────────────────
        self.fp_stage_ok = tk.Frame(self.fp_panel, bg=TM.get('bg','#0a0a14'))
        self.fp_sensor_ok = tk.Canvas(self.fp_stage_ok,
            width=130, height=130, bg=TM.get('bg','#0a0a14'), highlightthickness=0)
        self.fp_sensor_ok.pack(pady=(30, 6))
        self.fp_ok_title = tk.Label(self.fp_stage_ok,
                 text="FINGER 1 REGISTERED ✅",
                 font=("Inter 18pt", 13, "bold"),
                 bg=TM.get('bg','#0a0a14'), fg='#27ae60')
        self.fp_ok_title.pack()
        tk.Label(self.fp_stage_ok, text="Add 2nd finger as backup (optional)",
                 font=("Roboto", 9), bg=TM.get('bg','#0a0a14'), fg=TM.get('accent2','#7ecdc4')).pack(pady=4)
        btn_row = tk.Frame(self.fp_stage_ok, bg=TM.get('bg','#0a0a14'))
        btn_row.pack(fill=tk.X, padx=30, pady=6)
        GradientButton(btn_row, text="👆  Add 2nd Finger (Backup)",
            color1='#1a3a6b', color2='#0d2a5a',
            hover_color1='#2980B9', hover_color2='#1a5a9a',
            font=("Inter 18pt", 10, "bold"),
            height=42, command=self._scan_finger).pack(fill=tk.X, pady=3)
        GradientButton(btn_row, text="✅  Done — Save Student",
            color1='#1a5a1a', color2='#0d3a0d',
            hover_color1='#27ae60', hover_color2='#1a8a4a',
            font=("Inter 18pt", 10, "bold"),
            height=42, command=self._fp_done).pack(fill=tk.X, pady=3)

        # ── STAGE: FAIL ────────────────────────────────────────────────────────
        self.fp_stage_fail = tk.Frame(self.fp_panel, bg=TM.get('bg','#0a0a14'))
        tk.Label(self.fp_stage_fail, text="❌",
                 font=("Roboto", 64), bg=TM.get('bg','#0a0a14'), fg='#e74c3c').pack(pady=(40, 6))
        tk.Label(self.fp_stage_fail, text="SCAN FAILED",
                 font=("Inter 18pt", 13, "bold"),
                 bg=TM.get('bg','#0a0a14'), fg='#e74c3c').pack()
        self.fp_fail_lbl = tk.Label(self.fp_stage_fail, text="",
                 font=("Roboto", 9), bg=TM.get('bg','#0a0a14'), fg='#aaaaaa',
                 wraplength=380, justify=tk.CENTER)
        self.fp_fail_lbl.pack(pady=4)
        GradientButton(self.fp_stage_fail, text="🔄  Try Again",
            color1='#4a1a6b', color2='#2d0a5a',
            hover_color1='#7D3C98', hover_color2='#5a1a8a',
            font=("Inter 18pt", 10, "bold"),
            height=42, command=self._fp_retry).pack(fill=tk.X, padx=40, pady=10)

        # compat
        self.fp_panel_status = tk.Label(self.fp_panel, text="",
                 font=("Roboto", 1), bg=TM.get('bg','#0a0a14'), fg='#0a0a14')

        self._fp_show_stage('wait')
        self._draw_fp_sensor(self.fp_sensor_idle, 'idle')
        self._draw_fp_sensor(self.fp_sensor_ok, 'ok')

        # Apply initial method
        self._set_method('face')

    # ── Method switching ──────────────────────────────────────────────────────

    def _set_method(self, method):
        self.method_var.set(method)

        # Highlight selected method button
        for val, btn in self._method_btns.items():
            btn.config(bg='#00E5CC' if val == method else '#1a1a2e',
                       fg='#0d0d1a' if val == method else '#7ecdc4')

        # Stop camera if switching away from face mode
        if method == 'fingerprint' and self.camera_running:
            self._stop_camera()

        # Reset flags
        self.face_captured = False
        self.fp_verified   = False
        self.captured_frame = None
        self._reset_fp_btn()
        self.fp_panel_status.config(text="")
        self.save_btn.config_state(tk.DISABLED)
        self.cap_btn.config_state(tk.DISABLED)

        # ── Button layout based on mode ───────────────────────────────────────
        # Base y positions
        CAM_Y  = 330
        BH     = 38
        BG     = 6

        if method == 'face':
            # Camera + Capture + Save
            self.cam_btn.place(x=14, y=CAM_Y,         width=260, height=BH)
            self.cap_btn.place(x=14, y=CAM_Y+BH+BG,   width=260, height=BH)
            self.fp_btn.place_forget()
            self.save_btn.place(x=14, y=CAM_Y+(BH+BG)*2+4, width=260, height=42)
            self.status.place(  x=14, y=CAM_Y+(BH+BG)*2+52)

        elif method == 'fingerprint':
            # Fingerprint + Save (no camera)
            self.cam_btn.place_forget()
            self.cap_btn.place_forget()
            self.fp_btn.place(  x=14, y=CAM_Y,       width=260, height=BH)
            self.save_btn.place(x=14, y=CAM_Y+BH+BG+4, width=260, height=42)
            self.status.place(  x=14, y=CAM_Y+BH+BG+52)

        else:  # both
            # Camera + Capture + Fingerprint + Save
            self.cam_btn.place(x=14, y=CAM_Y,             width=260, height=BH)
            self.cap_btn.place(x=14, y=CAM_Y+BH+BG,       width=260, height=BH)
            self.fp_btn.place( x=14, y=CAM_Y+(BH+BG)*2,   width=260, height=BH)
            self.save_btn.place(x=14,y=CAM_Y+(BH+BG)*3+4, width=260, height=42)
            self.status.place(  x=14,y=CAM_Y+(BH+BG)*3+52)

        # ── Right panel ───────────────────────────────────────────────────────
        self.cam_placeholder.pack_forget()
        self.camera_label.pack_forget()
        self.fp_panel.pack_forget()

        if method == 'fingerprint':
            self.fp_panel.pack(fill=tk.BOTH, expand=True)
            self._fp_show_stage('wait')
            self._update_fp_count()
        else:
            self.cam_placeholder.pack(expand=True, fill=tk.BOTH)

        hints = {
            'face':        "⚡  Start Camera → Capture Face → Save",
            'fingerprint': "⚡  Click Verify Fingerprint → Save",
            'both':        "⚡  Capture Face + Verify Fingerprint → Save",
        }
        self.status.config(text=hints[method], fg='#f39c12')

    def _reset_fp_btn(self):
        self.fp_btn.color1 = '#4a1a6b'
        self.fp_btn.color2 = '#2d0a5a'
        self.fp_btn.text   = '👆  Verify Fingerprint'
        try: self.fp_btn._draw()
        except: pass

    def _check_save_ready(self):
        method = self.method_var.get()
        if method == 'face':
            ready = self.face_captured
        elif method == 'fingerprint':
            ready = self.fp_verified
        else:
            ready = self.face_captured and self.fp_verified
        self.save_btn.config_state(tk.NORMAL if ready else tk.DISABLED)

    # ── Camera ────────────────────────────────────────────────────────────────

    def _toggle_camera(self):
        if self.camera_running:
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self):
        try:
            self.capture = cv2.VideoCapture(0)
            if not self.capture.isOpened():
                messagebox.showerror("Error", "Cannot open camera!"); return
            self.camera_running = True
            self.cam_btn.color1 = '#1a5a1a'; self.cam_btn.color2 = '#0d3a0d'
            self.cam_btn.text   = '⏹  Stop Camera'
            self.cam_btn._draw()
            self.cap_btn.config_state(tk.NORMAL)
            self.cam_placeholder.pack_forget()
            self.fp_panel.pack_forget()
            self.camera_label.pack(fill=tk.BOTH, expand=True)
            self.status.config(
                text="📷  Camera on — click Capture Face", fg=TM.get('accent','#00E5CC'))
            self._update_camera()
        except Exception as e:
            messagebox.showerror("Error", f"Camera error: {e}")

    def _stop_camera(self):
        self.camera_running = False
        if self.capture:
            self.capture.release(); self.capture = None
        self.cam_btn.color1 = '#1a3a6b'; self.cam_btn.color2 = '#0d2a5a'
        self.cam_btn.text   = '📷  Start Camera'
        self.cam_btn._draw()
        self.cap_btn.config_state(tk.DISABLED)
        self.camera_label.pack_forget()
        self.cam_placeholder.pack(expand=True, fill=tk.BOTH)
        self.status.config(text="⚡  Camera stopped", fg='#f39c12')

    def _update_camera(self):
        if not self.camera_running: return
        if self.capture and self.capture.isOpened():
            ret, frame = self.capture.read()
            if ret:
                self.current_frame = frame.copy()   # <-- always keep fresh copy
                rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img   = Image.fromarray(rgb)
                w     = max(self.camera_label.winfo_width(),  320)
                h     = max(self.camera_label.winfo_height(), 240)
                img   = img.resize((w, h), Image.Resampling.LANCZOS)
                imgtk = ImageTk.PhotoImage(image=img)
                self.camera_label.imgtk = imgtk
                self.camera_label.configure(image=imgtk)
        self.window.after(30, self._update_camera)

    # ── Capture face ──────────────────────────────────────────────────────────

    def _capture_face(self):
        if self.current_frame is None:
            messagebox.showerror("Error",
                "No camera feed!\nStart the camera first."); return

        frame = self.current_frame.copy()

        # ── Validate face is actually detected before accepting ──────────────
        import face_recognition as fr
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locs  = fr.face_locations(rgb)

        if not locs:
            self.status.config(
                text="⚠  No face detected! Look straight at camera.",
                fg='#e74c3c')
            # Flash the camera preview red
            try:
                img = Image.fromarray(rgb)
                w   = max(self.camera_label.winfo_width(),  320)
                h   = max(self.camera_label.winfo_height(), 240)
                img = img.resize((w, h), Image.Resampling.LANCZOS)
                from PIL import ImageDraw
                draw = ImageDraw.Draw(img)
                draw.rectangle([0,0,w-1,h-1], outline=(255,50,50), width=6)
                draw.text((w//2-120, h//2), "NO FACE DETECTED", fill=(255,50,50))
                imgtk = ImageTk.PhotoImage(image=img)
                self.camera_label.imgtk = imgtk
                self.camera_label.configure(image=imgtk)
            except: pass
            return   # Do NOT capture

        self.captured_frame = frame
        self.face_captured  = True

        # ── Show frozen frame with green box around detected face ─────────────
        try:
            img = Image.fromarray(rgb)
            w   = max(self.camera_label.winfo_width(),  320)
            h   = max(self.camera_label.winfo_height(), 240)

            # Scale factor for drawing boxes
            orig_h, orig_w = rgb.shape[:2]
            sx = w / orig_w; sy = h / orig_h

            img = img.resize((w, h), Image.Resampling.LANCZOS)
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            # Green border
            draw.rectangle([0, 0, w-1, h-1], outline=(0, 229, 100), width=4)
            # Box around each detected face
            for (top, right, bottom, left) in locs:
                draw.rectangle(
                    [int(left*sx), int(top*sy),
                     int(right*sx), int(bottom*sy)],
                    outline=(0, 229, 100), width=3)
            imgtk = ImageTk.PhotoImage(image=img)
            self.camera_label.imgtk = imgtk
            self.camera_label.configure(image=imgtk)
        except: pass

        # Stop camera — keep frozen captured image visible
        self._stop_camera()
        self.camera_label.pack(fill=tk.BOTH, expand=True)
        self.cam_placeholder.pack_forget()

        self.status.config(
            text=f"✅  Face captured! ({len(locs)} face found) Click Save.",
            fg='#27ae60')
        self._check_save_ready()

    # ── Fingerprint ───────────────────────────────────────────────────────────

    def _draw_fp_sensor(self, canvas, state='idle'):
        """Draw fingerprint sensor graphic. state: idle/active/ok"""
        canvas.delete('all')
        c = {'idle': '#00E5CC', 'active': '#f39c12', 'ok': '#27ae60'}[state]
        canvas.create_oval(5, 5, 125, 125, outline=c, width=3, fill='#111128')
        for r in range(18, 52, 7):
            canvas.create_arc(65-r, 65-r, 65+r, 65+r,
                              start=210, extent=120,
                              outline=c, width=2, style='arc')
        canvas.create_oval(58, 58, 72, 72, fill=c, outline='')
        if state == 'ok':
            canvas.create_text(65, 100, text="✓ Scanned",
                               font=("Roboto", 9, "bold"), fill='#27ae60')
        elif state == 'active':
            canvas.create_text(65, 100, text="Scanning...",
                               font=("Roboto", 9), fill='#f39c12')

    def _fp_show_stage(self, stage):
        for f in [self.fp_stage_wait, self.fp_stage_scan,
                  self.fp_stage_ok, self.fp_stage_fail]:
            f.pack_forget()
        m = {'wait': self.fp_stage_wait, 'scan': self.fp_stage_scan,
             'ok': self.fp_stage_ok, 'fail': self.fp_stage_fail}
        if stage in m:
            m[stage].pack(fill=tk.BOTH, expand=True)

    def _fp_animate(self, step=0):
        frames = ["●  ○  ○", "○  ●  ○", "○  ○  ●", "●  ●  ○", "○  ●  ●"]
        try:
            if self._fp_scanning:
                self.fp_anim_lbl.config(text=frames[step % len(frames)])
                self.window.after(350, lambda: self._fp_animate(step+1))
        except: pass

    def _request_fp_permission(self):
        """Check Windows Hello is available when page opens."""
        self.status.config(text="🔐  Checking Windows Hello...", fg='#f39c12')
        self.window.update()

        def run():
            try:
                import asyncio
                import winrt.windows.security.credentials.ui as wh
                async def _v():
                    avail = await wh.UserConsentVerifier.check_availability_async()
                    return avail == wh.UserConsentVerifierAvailability.AVAILABLE
                loop = asyncio.new_event_loop()
                ok = loop.run_until_complete(_v())
                loop.close()
                if ok:
                    self.window.after(0, self._fp_permission_ok)
                else:
                    self.window.after(0, lambda: self._fp_permission_fail(
                        "Windows Hello not available.\nSet it up in Windows Settings."))
            except ImportError:
                self.window.after(0, lambda: self._fp_permission_fail(
                    "winrt not installed.\nRun: pip install winrt-runtime"))
            except Exception as e:
                self.window.after(0, lambda m=str(e): self._fp_permission_fail(m))

        threading.Thread(target=run, daemon=True).start()

    def _fp_permission_ok(self):
        try:
            self._fp_show_stage('wait')
            self._update_fp_count()
            self.status.config(
                text="✅  Permission granted — click Scan Finger", fg='#27ae60')
        except: pass

    def _fp_permission_fail(self, msg):
        try:
            self.status.config(text=f"❌  {msg[:60]}", fg='#e74c3c')
        except: pass

    def _update_fp_count(self):
        try:
            self.fp_finger_lbl.config(
                text=f"Fingers registered: {self.fp_fingers_registered} / 2")
        except: pass

    def _scan_finger(self):
        """Ask Windows Hello to verify — once per session only."""
        if self.fp_fingers_registered >= 2:
            return
        self._fp_scanning = True
        self._fp_show_stage('scan')
        self._fp_animate_sensor(0)
        self.status.config(text="🔐  Complete Windows Hello to register finger", fg='#f39c12')

        def run():
            try:
                import asyncio
                import winrt.windows.security.credentials.ui as wh
                async def _v():
                    r = await wh.UserConsentVerifier.request_verification_async(
                        f"Register finger {self.fp_fingers_registered + 1} of 2")
                    ok = r == wh.UserConsentVerificationResult.VERIFIED
                    return ok, "" if ok else "Not verified — try again"
                loop = asyncio.new_event_loop()
                ok, msg = loop.run_until_complete(_v())
                loop.close()
                self.window.after(0, lambda: self._scan_result(ok, msg))
            except ImportError:
                self.window.after(0, lambda: self._scan_result(
                    False, "winrt not installed"))
            except Exception as e:
                self.window.after(0, lambda m=str(e): self._scan_result(False, m))

        threading.Thread(target=run, daemon=True).start()

    def _fp_animate_sensor(self, step=0):
        """Pulsing fingerprint graphic while Hello is open."""
        try:
            if not self._fp_scanning:
                return
            cv = self.fp_scan_cv
            cv.delete('all')
            cx, cy = 80, 80
            pulse = (step % 16) * 3
            for i, r in enumerate([20, 35, 50, 62]):
                fade = max(20, 243 - pulse - i * 40)
                col = f'#{fade:02x}{int(fade*0.6):02x}12'
                cv.create_oval(cx-r-pulse//4, cy-r-pulse//4,
                               cx+r+pulse//4, cy+r+pulse//4,
                               outline=col, width=2)
            for r in range(10, 45, 8):
                cv.create_arc(cx-r, cy-r, cx+r, cy+r,
                              start=210, extent=120,
                              outline='#f39c12', width=2, style='arc')
            cv.create_oval(cx-5, cy-5, cx+5, cy+5, fill='#f39c12', outline='')
            msgs = ["Complete Hello prompt...", "Verifying...", "Hold steady..."]
            self.fp_anim_lbl.config(text=msgs[(step // 10) % len(msgs)])
            self.window.after(120, lambda: self._fp_animate_sensor(step + 1))
        except: pass

    def _stop_fp_camera(self):
        self._fp_scanning = False

    def _show_fp_img(self, photo):
        pass

    def _scan_result(self, ok, err=''):
        try:
            self._stop_fp_camera()
            if ok:
                self.fp_fingers_registered += 1
                self._update_fp_count()
                self._draw_fp_sensor(self.fp_sensor_ok, 'ok')
                if self.fp_fingers_registered >= 2:
                    self.fp_ok_title.config(text="BOTH FINGERS REGISTERED ✅")
                    self.window.after(600, self._fp_done)
                else:
                    self.fp_ok_title.config(
                        text=f"FINGER {self.fp_fingers_registered} REGISTERED ✅")
                self._fp_show_stage('ok')
                self.status.config(
                    text=f"✅  Finger {self.fp_fingers_registered} registered!",
                    fg='#27ae60')
            else:
                try:
                    self.fp_fail_lbl.config(
                        text=err or "Keep finger steady and try again.")
                except: pass
                self._fp_show_stage('fail')
                self.status.config(text="❌  Scan failed — try again", fg='#e74c3c')
        except: pass

    def _fp_retry(self):
        try:
            self._stop_fp_camera()
            self._fp_show_stage('wait')
            self.status.config(text="👆  Click Scan Finger to retry", fg='#f39c12')
        except: pass

    def _fp_done(self):
        try:
            if self.fp_fingers_registered == 0:
                return
            self.fp_verified = True
            self.fp_btn.color1 = '#1a6b3a'; self.fp_btn.color2 = '#0d4a5a'
            n = self.fp_fingers_registered
            self.fp_btn.text = f'✅  {n} Finger{"s" if n>1 else ""} Registered'
            self.fp_btn._draw()
            self.status.config(
                text=f"✅  {n} finger(s) registered! Fill form & click Save.",
                fg='#27ae60')
            self._check_save_ready()
        except: pass

    def _do_fingerprint(self):
        """Called by left-panel Verify button."""
        if fp_session.is_verified():
            self._fp_show_stage('wait')
            self.status.config(
                text="✅  Session active — click Scan Finger", fg='#27ae60')
        else:
            self._request_fp_permission()

    def _fp_not_available(self):
        try: self.status.config(text="⚠  winrt not installed", fg='#f39c12')
        except: pass
        try: messagebox.showerror("Not Available",
            "Run: pip install winrt-runtime\nOr use Face Only mode.")
        except: pass

    def _fp_fail(self, msg):
        try:
            self.fp_fail_lbl.config(text=msg[:60])
            self._fp_show_stage('fail')
            self.status.config(text="❌  Failed", fg='#e74c3c')
        except: pass

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save_student(self):
        name   = self.e_name.get_real()
        father = self.e_father.get_real()
        roll   = self.e_roll.get_real()
        reg    = self.e_reg.get_real()
        sem    = int(self.sem_var.get())
        method = self.method_var.get()

        if not all([name, father, roll, reg]):
            messagebox.showerror("Error", "Fill in ALL fields!"); return

        if method in ('face', 'both') and self.captured_frame is None:
            messagebox.showerror("Error", "Capture a face photo first!"); return

        if method in ('fingerprint', 'both') and not self.fp_verified:
            messagebox.showerror("Error", "Verify fingerprint first!"); return

        # Save face image
        image_path = "no_image.jpg"
        if self.captured_frame is not None:
            os.makedirs("students", exist_ok=True)
            filename   = f"sem{sem}_{roll}_{name.replace(' ','_')}.jpg"
            image_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "students", filename)
            ret = cv2.imwrite(image_path, self.captured_frame)
            if not ret:
                messagebox.showerror("Error",
                    f"Could not save image to:\n{image_path}"); return

        success, msg = self.db.add_student(
            name, father, roll, reg, sem, image_path, method)

        if success:
            labels = {'face':        'Face Recognition',
                      'fingerprint': 'Fingerprint',
                      'both':        'Face + Fingerprint'}
            messagebox.showinfo("✅ Registered",
                f"Student '{name}' saved!\n"
                f"Semester: {sem}   Roll: {roll}\n"
                f"Method: {labels[method]}")
            self._clear_form()
        else:
            if os.path.exists(image_path) and image_path != "no_image.jpg":
                os.remove(image_path)
            messagebox.showerror("Error", msg)

    def _clear_form(self):
        for e, ph in [
            (self.e_name,   "Full name"),
            (self.e_father, "Father's full name"),
            (self.e_roll,   "e.g. 2021-CS-01"),
            (self.e_reg,    "e.g. 2021-BSCS-123"),
        ]:
            e.delete(0, tk.END); e.insert(0, ph)
            e.config(fg='#666688')
        self.sem_var.set("1")
        self.current_frame  = None
        self.captured_frame = None
        self.face_captured  = False
        self.fp_verified    = False
        self._reset_fp_btn()
        self.fp_panel_status.config(text="")
        self.save_btn.config_state(tk.DISABLED)
        self.cap_btn.config_state(tk.DISABLED)
        # Reset right panel
        self.camera_label.pack_forget()
        self.fp_panel.pack_forget()
        self.cam_placeholder.pack(expand=True, fill=tk.BOTH)
        hints = {
            'face':        "⚡  Start Camera → Capture Face → Save",
            'fingerprint': "⚡  Click Verify Fingerprint → Save",
            'both':        "⚡  Capture Face + Verify Fingerprint → Save",
        }
        self.status.config(
            text=hints[self.method_var.get()], fg='#f39c12')

    def _on_close(self):
        self._stop_camera()
        self._stop_fp_camera()
        self.window.destroy()


# ── Placeholder Entry ─────────────────────────────────────────────────────────

class _PlaceholderEntry(tk.Entry):
    def __init__(self, master, placeholder, **kw):
        super().__init__(master, **kw)
        self._ph = placeholder
        self.insert(0, placeholder)
        self.config(fg='#666688', bd=0,
                    highlightthickness=0,
                    relief=tk.FLAT)
        self.bind('<FocusIn>',  self._in)
        self.bind('<FocusOut>', self._out)

    def _in(self, e):
        if self.get() == self._ph:
            self.delete(0, tk.END)
        self.config(fg='white')

    def _out(self, e):
        if not self.get():
            self.insert(0, self._ph)
            self.config(fg='#666688')

    def get_real(self):
        v = self.get()
        return '' if v == self._ph else v.strip()