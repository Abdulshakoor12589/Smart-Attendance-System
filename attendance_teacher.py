# attendance_teacher.py — Teacher selects name/semester/subject → time-gated attendance
import tkinter as tk
from tkinter import ttk, messagebox
import os, sys, threading
from datetime import datetime, date
from PIL import Image, ImageTk, ImageFilter, ImageEnhance
import face_recognition
import cv2
from database import Database
from gradient import GradientFrame, GradientButton
import theme as TM
import fp_session


def get_base_dir():
    if getattr(sys, 'frozen', False):
        # PyInstaller stores files in _MEIPASS when running as .exe
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _set_app_icon(win):
    for name in ["favicon.png", "favicon.ico"]:
        p = os.path.join(get_base_dir(), name)
        if os.path.exists(p):
            try:
                img = tk.PhotoImage(file=p)
                win.iconphoto(False, img); win._icon_ref = img
            except: pass
            break


class TeacherAttendanceWindow:
    def __init__(self, parent, container=None):
        # If container given, render inside it (in-place mode)
        # Otherwise open as standalone Toplevel
        if container is not None:
            self.window = container
            self.standalone = False
        else:
            self.window = tk.Toplevel(parent)
            self.window.title("Door Attendance System")
            self.window.resizable(True, True)
            self.window.transient(parent)
            sw = self.window.winfo_screenwidth()
            sh = self.window.winfo_screenheight()
            W = min(1300, sw-40); H = min(800, sh-40)
            self.window.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
            self.W, self.H = W, H
            _set_app_icon(self.window)
            self.standalone = True
        self.db = Database()
        try:
            import json
            s = json.load(open(os.path.join(get_base_dir(),"app_settings.json")))
            self._time_fmt = s.get("time_format","12h")
        except:
            self._time_fmt = "12h"

        # State
        self.capture        = None
        self.is_running     = False
        self.current_frame  = None
        self.known_encodings = []
        self.known_names    = []
        self.known_rolls    = []
        self.known_ids      = []
        self.known_sems     = []
        self.known_methods  = []
        self.marked_today   = set()
        self._refs          = {}

        # Selected class info
        self.sel_teacher = tk.StringVar()
        self.sel_subject = tk.StringVar()
        self.sel_sem     = tk.IntVar(value=0)
        self.sel_time_start = ''
        self.sel_time_end   = ''

        self._mode = 'face'   # face / fingerprint

        self._build_ui()
        self._populate_teachers()
        if self.standalone: self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── bg ────────────────────────────────────────────────────────────────────

    def _draw_bg(self):
        w = self.window.winfo_width()  or self.W
        h = self.window.winfo_height() or self.H
        for name in ["tb.jpg","tb.JPG"]:
            p = os.path.join(get_base_dir(), name)
            if os.path.exists(p):
                img = Image.open(p).resize((w,h), Image.Resampling.LANCZOS)
                img = ImageEnhance.Brightness(img).enhance(0.22)
                img = img.filter(ImageFilter.GaussianBlur(5))
                ph  = ImageTk.PhotoImage(img)
                self._refs['bg'] = ph
                self.bg_cv.delete('bg')
                self.bg_cv.create_image(0,0,image=ph,anchor='nw',tags='bg')
                self.bg_cv.tag_lower('bg')
                break

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.bg_cv = tk.Canvas(self.window, highlightthickness=0, bd=0)
        self.bg_cv.place(x=0,y=0, relwidth=1, relheight=1)
        self.window.bind('<Configure>',
            lambda e: self._draw_bg() if e.widget is self.window else None)
        self._draw_bg()

        # Header
        hdr = GradientFrame(self.window, TM.get('header_grad1','#0d0d2e'), TM.get('header_grad2','#001a1a'), height=58)
        hdr.place(x=0,y=0, relwidth=1)
        def dh(e,h=hdr):
            h._on_resize(e); h.delete('w')
            h.create_text(e.width//2, 29,
                text="🚪   SMART DOOR ATTENDANCE",
                font=("Inter 18pt",16,"bold"), fill='#00E5CC', tags='w')
        hdr.bind('<Configure>', dh)
        tk.Frame(self.window, bg='#00E5CC', height=2).place(x=0,y=58, relwidth=1)

        # ── Teacher selector strip — ONE ROW ─────────────────────────────────
        sel = tk.Frame(self.window, bg=TM.get('panel','#080818'), height=60)
        sel.place(x=0, y=60, relwidth=1)

        lkw = dict(font=("Inter 18pt",8,"bold"), bg=TM.get('panel','#080818'), fg=TM.get('accent','#00E5CC'))
        dd  = dict(font=("Roboto",9), bg=TM.get('entry_bg','#1a1a2e'), fg='white',
                   activebackground='#2a2a4e', activeforeground='#00E5CC',
                   relief=tk.FLAT, highlightthickness=0)

        # Teacher Name
        tk.Label(sel, text="Teacher:", **lkw).place(x=10, y=8)
        self.teacher_menu = tk.OptionMenu(sel, self.sel_teacher, "—")
        self.teacher_menu.config(**dd, width=16)
        self.teacher_menu["menu"].config(bg=TM.get('entry_bg','#1a1a2e'), fg='white',
            activebackground='#2a2a4e', font=("Roboto",9))
        self.teacher_menu.place(x=10, y=26)
        self.sel_teacher.trace_add('write', self._on_teacher_change)

        # Semester
        tk.Label(sel, text="Semester:", **lkw).place(x=220, y=8)
        self.sem_dd = tk.OptionMenu(sel, self.sel_sem, 0)
        self.sem_dd.config(**dd, width=8)
        self.sem_dd["menu"].config(bg=TM.get('entry_bg','#1a1a2e'), fg='white',
            activebackground='#2a2a4e', font=("Roboto",9))
        self.sem_dd.place(x=220, y=26)
        self.sel_sem.trace_add('write', self._on_sem_change)

        # Subject
        tk.Label(sel, text="Subject:", **lkw).place(x=370, y=8)
        self.subj_dd = tk.OptionMenu(sel, self.sel_subject, "—")
        self.subj_dd.config(**dd, width=16)
        self.subj_dd["menu"].config(bg=TM.get('entry_bg','#1a1a2e'), fg='white',
            activebackground='#2a2a4e', font=("Roboto",9))
        self.subj_dd.place(x=370, y=26)
        self.sel_subject.trace_add('write', self._on_subject_change)

        # Time label
        self.time_lbl = tk.Label(sel,
            text="🕐  —",
            font=("Roboto",8,"bold"), bg=TM.get('panel','#080818'), fg='#f39c12')
        self.time_lbl.place(x=570, y=32)

        # Face / Fingerprint toggle
        self.face_btn = tk.Button(sel, text="📷  Face",
            font=("Inter 18pt",8,"bold"), relief=tk.FLAT, cursor='hand2',
            padx=8, pady=2, bg='#00E5CC', fg='#0d0d1a',
            command=lambda: self._set_mode('face'))
        self.face_btn.place(x=760, y=26)

        self.fp_btn = tk.Button(sel, text="👆  Fingerprint",
            font=("Inter 18pt",8,"bold"), relief=tk.FLAT, cursor='hand2',
            padx=8, pady=2, bg=TM.get('entry_bg','#1a1a2e'), fg=TM.get('accent2','#7ecdc4'),
            command=lambda: self._set_mode('fingerprint'))
        self.fp_btn.place(x=840, y=26)

        # START button
        self.start_btn = GradientButton(sel,
            text="▶  START ATTENDANCE",
            color1='#1a5a1a', color2='#0d3a0d',
            hover_color1='#27ae60', hover_color2='#1a8a4a',
            font=("Inter 18pt",9,"bold"),
            width=190, height=32,
            command=self._start_attendance)
        self.start_btn.place(x=1060, y=14)

        tk.Frame(self.window, bg='#1a1a3e', height=1).place(x=0, y=120, relwidth=1)

        # ── Body: camera left + info right ───────────────────────────────────
        BODY_Y = 122
        RIGHT_W = 320

        # Camera panel
        cam_outer = tk.Frame(self.window, bg='#00E5CC', bd=1)
        cam_outer.place(x=0, y=BODY_Y,
                         relwidth=1, width=-(RIGHT_W+4),
                         relheight=1, height=-BODY_Y)
        self.cam_inner = tk.Frame(cam_outer, bg=TM.get('bg','#060610'))
        self.cam_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        self.cam_placeholder = tk.Label(self.cam_inner,
            text="📷\n\nCamera is off\nClick  ▶ START ATTENDANCE",
            font=("Roboto",14), bg=TM.get('bg','#060610'), fg='#333355',
            justify=tk.CENTER)
        self.cam_placeholder.pack(expand=True, fill=tk.BOTH)
        self.cam_lbl = tk.Label(self.cam_inner, bg='black')

        # ── Right info panel ──────────────────────────────────────────────────
        right = tk.Frame(self.window, bg=TM.get('panel','#0a0a18'),
                          highlightthickness=1,
                          highlightbackground='#1a1a3e')
        right.place(relx=1.0, x=-(RIGHT_W), y=BODY_Y,
                     width=RIGHT_W,
                     relheight=1, height=-BODY_Y)

        # Status
        self.status_cv = tk.Canvas(right, bg=TM.get('header_grad1','#0d0d2e'),
                                    height=80, highlightthickness=0)
        self.status_cv.pack(fill=tk.X)
        self.status_cv.bind('<Configure>',
            lambda e: self._draw_status("⚪", "READY", "Select class & click START"))

        # Last marked
        tk.Label(right, text="LAST MARKED",
                 font=("Inter 18pt",9,"bold"),
                 bg=TM.get('panel','#0a0a18'), fg=TM.get('accent','#00E5CC')).pack(
                     anchor='w', padx=14, pady=(10,2))
        self.last_frame = tk.Frame(right, bg='#111128')
        self.last_frame.pack(fill=tk.X, padx=10, pady=2)
        self.lbl_name   = tk.Label(self.last_frame, text="Name: —",
            font=("Roboto",9), bg='#111128', fg='#cccccc', anchor='w')
        self.lbl_roll   = tk.Label(self.last_frame, text="Roll: —",
            font=("Roboto",9), bg='#111128', fg='#cccccc', anchor='w')
        self.lbl_time   = tk.Label(self.last_frame, text="Time: —",
            font=("Roboto",9), bg='#111128', fg='#cccccc', anchor='w')
        self.lbl_method = tk.Label(self.last_frame, text="Method: —",
            font=("Roboto",9), bg='#111128', fg='#cccccc', anchor='w')
        for l in [self.lbl_name,self.lbl_roll,self.lbl_time,self.lbl_method]:
            l.pack(anchor='w', padx=10, pady=1)

        # Stats
        tk.Label(right, text="TODAY'S STATISTICS",
                 font=("Inter 18pt",9,"bold"),
                 bg=TM.get('panel','#0a0a18'), fg=TM.get('accent','#00E5CC')).pack(
                     anchor='w', padx=14, pady=(10,2))
        self.stats_lbl = tk.Label(right,
            text="Total: 0  |  Present: 0  |  Absent: 0",
            font=("Roboto",9), bg=TM.get('panel','#0a0a18'), fg=TM.get('accent2','#7ecdc4'))
        self.stats_lbl.pack(anchor='w', padx=14)

        # Activity log
        tk.Label(right, text="ACTIVITY LOG",
                 font=("Inter 18pt",9,"bold"),
                 bg=TM.get('panel','#0a0a18'), fg=TM.get('accent','#00E5CC')).pack(
                     anchor='w', padx=14, pady=(10,2))
        log_f = tk.Frame(right, bg=TM.get('bg','#0a0a14'))
        log_f.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        lsb = tk.Scrollbar(log_f, bg=TM.get('entry_bg','#1a1a2e'), troughcolor='#0a0a14')
        lsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_box = tk.Listbox(log_f,
            font=("Roboto",8), bg=TM.get('bg','#0a0a14'), fg=TM.get('accent2','#7ecdc4'),
            selectbackground='#1a3a6b', relief=tk.FLAT,
            yscrollcommand=lsb.set, highlightthickness=0)
        self.log_box.pack(fill=tk.BOTH, expand=True)
        lsb.config(command=self.log_box.yview)

        # STOP button (bottom)
        self.stop_btn = GradientButton(right,
            text="⏹  STOP",
            color1='#6b0000', color2='#4a0000',
            hover_color1='#C0392B', hover_color2='#922B21',
            font=("Inter 18pt",10,"bold"),
            height=38, command=self._stop_attendance)
        self.stop_btn.pack(fill=tk.X, padx=10, pady=6)

        # Fingerprint panel (hidden by default)
        self.fp_panel = tk.Frame(self.cam_inner, bg=TM.get('bg','#060610'))
        tk.Label(self.fp_panel, text="👆",
                 font=("Roboto",64), bg=TM.get('bg','#060610'),
                 fg=TM.get('accent','#00E5CC')).pack(pady=(40,8))
        tk.Label(self.fp_panel, text="FINGERPRINT ATTENDANCE",
                 font=("Inter 18pt",14,"bold"),
                 bg=TM.get('bg','#060610'), fg=TM.get('accent','#00E5CC')).pack()
        self.fp_name_lbl = tk.Label(self.fp_panel, text="",
            font=("Roboto",11), bg=TM.get('bg','#060610'), fg=TM.get('accent2','#7ecdc4'))
        self.fp_name_lbl.pack(pady=4)

        self.fp_dd_var = tk.StringVar()
        self.fp_dropdown = tk.OptionMenu(self.fp_panel, self.fp_dd_var, "—")
        self.fp_dropdown.config(font=("Roboto",11),
            bg=TM.get('entry_bg','#1a1a2e'), fg='white', relief=tk.FLAT,
            activebackground='#2a2a4e', width=28)
        self.fp_dropdown.pack(pady=8)

        GradientButton(self.fp_panel,
            text="👆  Verify Fingerprint & Mark Present",
            color1='#4a1a6b', color2='#2d0a5a',
            hover_color1='#7D3C98', hover_color2='#5a1a8a',
            font=("Inter 18pt",11,"bold"),
            height=44, command=self._do_fingerprint
        ).pack(fill=tk.X, padx=40, pady=8)

        self.fp_status = tk.Label(self.fp_panel, text="",
            font=("Roboto",10,"bold"),
            bg=TM.get('bg','#060610'), fg='#f39c12')
        self.fp_status.pack()

    # ── Teacher dropdowns ─────────────────────────────────────────────────────

    def _populate_teachers(self):
        teachers = self.db.get_all_teachers()
        menu = self.teacher_menu["menu"]
        menu.delete(0, tk.END)
        if not teachers:
            menu.add_command(label="No teachers configured",
                command=lambda: self.sel_teacher.set("—"))
            self.sel_teacher.set("—")
            return
        for t in teachers:
            menu.add_command(label=t,
                command=lambda v=t: self.sel_teacher.set(v))
        self.sel_teacher.set(teachers[0])

    def _on_teacher_change(self, *_):
        teacher = self.sel_teacher.get()
        if not teacher or teacher == "—": return
        rows = self.db.get_subjects_for_teacher(teacher)
        # rows: subject, semester, time_start, time_end

        sems = sorted(set(r[1] for r in rows))
        menu = self.sem_dd["menu"]
        menu.delete(0, tk.END)
        for s in sems:
            menu.add_command(label=f"Semester {s}",
                command=lambda v=s: self.sel_sem.set(v))
        if sems:
            self.sel_sem.set(sems[0])

    def _on_sem_change(self, *_):
        teacher = self.sel_teacher.get()
        sem     = self.sel_sem.get()
        if not teacher or teacher == "—" or sem == 0: return

        rows = self.db.get_subjects_for_teacher(teacher)
        subjects = [(r[0], r[2], r[3]) for r in rows if r[1] == sem]

        menu = self.subj_dd["menu"]
        menu.delete(0, tk.END)
        self._subj_map = {}
        for subj, ts, te in subjects:
            self._subj_map[subj] = (ts, te)
            menu.add_command(label=subj,
                command=lambda v=subj: self.sel_subject.set(v))
        if subjects:
            self.sel_subject.set(subjects[0][0])

        # ── Pre-load students for this semester in background ─────────────────
        # So face encodings are ready before START is clicked
        import threading
        threading.Thread(
            target=self._preload_students, args=(sem,), daemon=True).start()

    def _preload_students(self, sem):
        """Load & encode student faces in background as soon as semester changes."""
        self._log(f"⏳ Pre-loading Semester {sem} students...")
        self._load_students(sem)
        self._log(f"✅ Semester {sem}: {len(self.known_names)} student(s) ready")

    def _on_subject_change(self, *_):
        subj = self.sel_subject.get()
        if not hasattr(self, '_subj_map') or subj not in self._subj_map:
            return
        ts, te = self._subj_map[subj]
        self.sel_time_start = ts
        self.sel_time_end   = te
        # Reload time format preference
        try:
            import json as _j
            _s = _j.load(open(os.path.join(get_base_dir(), "app_settings.json")))
            self._time_fmt = _s.get("time_format", "12h")
        except:
            self._time_fmt = "12h"
        def _fmt(t):
            try:
                h, m = map(int, t.split(':'))
                if self._time_fmt == '12h':
                    return f"{h%12 or 12}:{m:02d} {'AM' if h<12 else 'PM'}"
                return t
            except: return t
        self.time_lbl.config(
            text=f"🕐  {_fmt(ts)}  →  {_fmt(te)}",
            fg='#f39c12')

    def _set_mode(self, mode):
        self._mode = mode
        self.face_btn.config(
            bg='#00E5CC' if mode=='face' else '#1a1a2e',
            fg='#0d0d1a' if mode=='face' else '#7ecdc4')
        self.fp_btn.config(
            bg='#00E5CC' if mode=='fingerprint' else '#1a1a2e',
            fg='#0d0d1a' if mode=='fingerprint' else '#7ecdc4')

    # ── Status canvas ─────────────────────────────────────────────────────────

    def _draw_status(self, dot, title, sub):
        c = self.status_cv
        c.delete('all')
        w = c.winfo_width()
        if w < 10: w = RIGHT_W = 320
        c.create_text(w//2, 28, text=f"{dot}  {title}",
            font=("Inter 18pt",13,"bold"), fill='#00E5CC')
        c.create_text(w//2, 56, text=sub,
            font=("Roboto",9), fill='#7ecdc4')

    # ── Log ───────────────────────────────────────────────────────────────────

    def _log(self, msg):
        t = datetime.now().strftime('%H:%M:%S')
        self.log_box.insert(tk.END, f"[{t}] {msg}")
        self.log_box.see(tk.END)

    # ── Start / Stop ──────────────────────────────────────────────────────────

    def _start_attendance(self):
        teacher = self.sel_teacher.get()
        subject = self.sel_subject.get()
        sem     = self.sel_sem.get()

        if not teacher or teacher == "—":
            messagebox.showerror("Error", "Select a teacher first."); return
        if not subject or subject == "—":
            messagebox.showerror("Error", "Select a subject first."); return
        if sem == 0:
            messagebox.showerror("Error", "Select a semester first."); return

        # ── Time check ────────────────────────────────────────────────────────
        if self.sel_time_start and self.sel_time_end:
            now = datetime.now().strftime('%H:%M')
            ts  = self.sel_time_start
            te  = self.sel_time_end
            if not (ts <= now <= te):
                messagebox.showerror("⏰  Not Your Class Time",
                    f"This class runs  {ts}  →  {te}\n\n"
                    f"Current time is  {now}\n\n"
                    "Attendance can only be taken during class time.")
                return

        self._log(f"Starting: {teacher} | {subject} | Sem {sem}")
        self._load_students(sem)

        if self._mode == 'face':
            self._start_camera()
        else:
            self._show_fp_panel(sem)

    def _stop_attendance(self):
        self.is_running = False
        if self.capture:
            self.capture.release(); self.capture = None
        self.cam_lbl.pack_forget()
        self.fp_panel.pack_forget()
        self.cam_placeholder.pack(expand=True, fill=tk.BOTH)
        self._draw_status("⚪","READY","Select class & click START")
        self._log("Attendance stopped.")

    # ── Load students ─────────────────────────────────────────────────────────

    def _load_students(self, sem):
        # Only load students from this specific semester — no cross-semester matching
        self.known_encodings = []
        self.known_names  = []
        self.known_rolls  = []
        self.known_ids    = []
        self.known_sems   = []
        self.known_methods = []
        self._current_sem = sem

        students = self.db.get_students_by_semester(sem)
        self._log(f"🎓 Semester {sem}: {len(students)} student(s) found")

        for s in students:
            sid      = s[0]; name = s[1]; roll = s[3]
            img_path = s[6]
            method   = s[8] if len(s)>8 else 'face'

            if method in ('face','both') and os.path.exists(img_path):
                try:
                    img  = face_recognition.load_image_file(img_path)
                    encs = face_recognition.face_encodings(img)
                    enc  = encs[0] if encs else None
                except: enc = None
            else:
                enc = None

            self.known_encodings.append(enc)
            self.known_names.append(name)
            self.known_rolls.append(roll)
            self.known_ids.append(sid)
            self.known_sems.append(sem)
            self.known_methods.append(method)
            self._log(f"  {'✓' if enc is not None else '·'} {name} [{method}]")

        self._update_stats()

        # Populate fingerprint dropdown
        fp_students = [self.known_names[i]
                       for i in range(len(self.known_names))
                       if self.known_methods[i] in ('fingerprint','both')]
        menu = self.fp_dropdown["menu"]
        menu.delete(0, tk.END)
        for n in fp_students:
            menu.add_command(label=n,
                command=lambda v=n: self.fp_dd_var.set(v))
        if fp_students:
            self.fp_dd_var.set(fp_students[0])

    # ── Camera / face ─────────────────────────────────────────────────────────

    def _start_camera(self):
        face_idx = [i for i in range(len(self.known_names))
                    if self.known_methods[i] in ('face','both')
                    and self.known_encodings[i] is not None]
        if not face_idx:
            messagebox.showerror("Error",
                "No students with face data found for this semester.\n"
                "Register students using Face or Both method."); return

        self.capture = cv2.VideoCapture(0)
        if not self.capture.isOpened():
            messagebox.showerror("Error","Cannot open camera."); return

        self.is_running = True
        self.cam_placeholder.pack_forget()
        self.fp_panel.pack_forget()
        self.cam_lbl.pack(fill=tk.BOTH, expand=True)
        self._draw_status("🟢","RUNNING","Face recognition active")
        self._log(f"Camera started — {len(face_idx)} face(s) loaded")
        self._update_camera()

    def _update_camera(self):
        if not self.is_running: return
        if self.capture and self.capture.isOpened():
            ret, frame = self.capture.read()
            if ret:
                self.current_frame = frame.copy()
                rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                locs  = face_recognition.face_locations(rgb, model='hog')
                encs  = face_recognition.face_encodings(rgb, locs)

                face_idx = [i for i in range(len(self.known_names))
                            if self.known_methods[i] in ('face','both')
                            and self.known_encodings[i] is not None]
                known_enc = [self.known_encodings[i] for i in face_idx]

                for (top,right,bottom,left), enc in zip(locs, encs):
                    matches = face_recognition.compare_faces(
                        known_enc, enc, tolerance=0.5)
                    name_lbl = "Unknown"; color=(255,50,50)
                    if True in matches:
                        best = face_recognition.face_distance(
                            known_enc, enc).argmin()
                        if matches[best]:
                            real_i = face_idx[best]
                            n = self.known_names[real_i]
                            r = self.known_rolls[real_i]
                            sid = self.known_ids[real_i]
                            sem = self.known_sems[real_i]
                            name_lbl = n; color=(0,229,100)
                            if r not in self.marked_today:
                                self.marked_today.add(r)
                                self._mark_present(sid, n, r, sem, 'Face')

                    cv2.rectangle(frame,(left,top),(right,bottom),color,2)
                    cv2.putText(frame, name_lbl,(left,top-8),
                        cv2.FONT_HERSHEY_SIMPLEX,0.6,color,2)

                rgb2  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img   = Image.fromarray(rgb2)
                ww    = max(self.cam_lbl.winfo_width(), 640)
                hh    = max(self.cam_lbl.winfo_height(), 480)
                img   = img.resize((ww,hh), Image.Resampling.LANCZOS)
                imgtk = ImageTk.PhotoImage(image=img)
                self.cam_lbl.imgtk = imgtk
                self.cam_lbl.configure(image=imgtk)

        self.window.after(30, self._update_camera)

    # ── Fingerprint panel ─────────────────────────────────────────────────────

    def _show_fp_panel(self, sem):
        self.cam_placeholder.pack_forget()
        self.cam_lbl.pack_forget()
        teacher = self.sel_teacher.get()
        subj    = self.sel_subject.get()
        self.fp_name_lbl.config(
            text=f"Teacher: {teacher}  |  {subj}  |  Sem {sem}")
        self.fp_panel.pack(fill=tk.BOTH, expand=True)
        self._draw_status("🟢","READY","Select student & verify fingerprint")
        self._log("Fingerprint mode active")

    def _do_fingerprint(self):
        name = self.fp_dd_var.get()
        if not name or name == "—":
            messagebox.showerror("Error", "Select a student first."); return

        # Session already verified — mark directly, no Hello popup
        if fp_session.is_verified():
            self._fp_mark(name)
            return

        # Very first use this session — ask Hello ONCE only
        try: self.fp_status.config(
            text="⏳  Windows Hello — one-time check...", fg=TM.get('accent','#00E5CC'))
        except: pass
        self.window.update()

        def run():
            try:
                import asyncio
                import winrt.windows.security.credentials.ui as wh
                async def _v():
                    avail = await wh.UserConsentVerifier.check_availability_async()
                    if avail != wh.UserConsentVerifierAvailability.AVAILABLE:
                        return False
                    r = await wh.UserConsentVerifier.request_verification_async(
                        "Smart Attendance — one-time session check")
                    return r == wh.UserConsentVerificationResult.VERIFIED
                loop = asyncio.new_event_loop()
                ok = loop.run_until_complete(_v())
                loop.close()
                if ok:
                    fp_session.set_verified(True)
                    self.window.after(0, lambda n=name: self._fp_mark(n))
                else:
                    self.window.after(0, lambda: self._safe_fp(
                        "❌  Cancelled", '#e74c3c'))
            except ImportError:
                self.window.after(0, lambda: self._safe_fp(
                    "⚠  winrt not installed", '#f39c12'))
            except Exception as e:
                self.window.after(0, lambda err=str(e): self._safe_fp(
                    f"❌  {err[:40]}", '#e74c3c'))

        import threading
        threading.Thread(target=run, daemon=True).start()

    def _safe_fp(self, text, color):
        try: self.fp_status.config(text=text, fg=color)
        except: pass

    def _fp_mark(self, name):
        try:
            idx = next((i for i,n in enumerate(self.known_names) if n==name), None)
            if idx is None: return
            roll = self.known_rolls[idx]
            if roll in self.marked_today:
                self._safe_fp(f"ℹ  {name} already marked", '#f39c12'); return
            self.marked_today.add(roll)
            self._mark_present(self.known_ids[idx], name, roll,
                               self.known_sems[idx], 'Fingerprint')
            self._safe_fp(f"✅  {name} marked Present!", '#27ae60')
        except Exception: pass
    def _mark_present(self, sid, name, roll, sem, method_label):
        today = date.today().strftime('%Y-%m-%d')
        t     = datetime.now().strftime('%H:%M:%S')
        teacher = self.sel_teacher.get()
        subject = self.sel_subject.get()

        def do():
            self.db.add_attendance_with_class(
                sid, name, roll, sem, today, t, 'Present',
                teacher, subject)
            self.window.after(0, lambda: self._on_marked(name, roll, t, method_label))
            self._log(f"✓ PRESENT [{method_label}]: {name}  @{t}")

        import threading
        threading.Thread(target=do, daemon=True).start()

    def _on_marked(self, name, roll, t, method):
        self.lbl_name.config(text=f"Name: {name}")
        self.lbl_roll.config(text=f"Roll: {roll}")
        self.lbl_time.config(text=f"Time: {t}")
        self.lbl_method.config(text=f"Method: {method}")
        self._update_stats()
        self._draw_status("🟢","PRESENT",f"{name} marked ✓")

    def _update_stats(self):
        total   = len(self.known_names)
        present = len(self.marked_today)
        absent  = total - present
        self.stats_lbl.config(
            text=f"Total: {total}  |  Present: {present}  |  Absent: {absent}")

    def _on_close(self):
        self.is_running = False
        if self.capture: self.capture.release()
        self.window.destroy()