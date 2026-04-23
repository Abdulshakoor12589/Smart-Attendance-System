# registered_students.py - Dark theme matching other pages
import tkinter as tk
from tkinter import ttk, messagebox
import os, sys
from PIL import Image, ImageTk, ImageFilter, ImageEnhance
from database import Database
from gradient import GradientFrame, GradientButton
import theme as TM
from datetime import datetime


def get_base_dir():
    if getattr(sys, 'frozen', False):
        # PyInstaller stores files in _MEIPASS when running as .exe
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


class RegisteredStudentsWindow:
    def __init__(self, parent, container=None):
        W, H = 1200, 740
        if container is not None:
            self.window = container
            self.standalone = False
        else:
            self.window = tk.Toplevel(parent)
            self.window.title("Registered Students")
            self.window.resizable(True, True)
            self.window.transient(parent)
            sw = self.window.winfo_screenwidth()
            sh = self.window.winfo_screenheight()
            W = min(1200, sw - 40)
            H = min(740,  sh - 40)
            self.window.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
            self.W, self.H = W, H
            self._set_icon()
            self.standalone = True

        self.db               = Database()
        self.current_semester = 1
        self._selected_iid    = None
        self._refs            = {}

        self._build_ui()
        self._load(1)
        if self.standalone: self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)

    def _set_icon(self):
        for name in ["favicon.png", "favicon.ico"]:
            path = os.path.join(get_base_dir(), name)
            if os.path.exists(path):
                try:
                    img = tk.PhotoImage(file=path)
                    self.window.iconphoto(False, img)
                    self._icon = img
                except: pass
                break

    # ── background ────────────────────────────────────────────────────────────

    def _draw_bg(self):
        w = self.window.winfo_width()  or self.W
        h = self.window.winfo_height() or self.H
        for name in ["tb.jpg", "tb.JPG"]:
            path = os.path.join(get_base_dir(), name)
            if os.path.exists(path):
                img = Image.open(path).resize((w, h), Image.Resampling.LANCZOS)
                img = ImageEnhance.Brightness(img).enhance(0.22)
                img = img.filter(ImageFilter.GaussianBlur(5))
                photo = ImageTk.PhotoImage(img)
                self._refs['bg'] = photo
                self.bg_canvas.delete('bg')
                self.bg_canvas.create_image(0, 0, image=photo, anchor='nw', tags='bg')
                self.bg_canvas.tag_lower('bg')
                break

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Background
        self.bg_canvas = tk.Canvas(self.window, highlightthickness=0, bd=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.window.bind('<Configure>',
            lambda e: self._draw_bg() if e.widget is self.window else None)
        self._draw_bg()

        # ── Header ────────────────────────────────────────────────────────────
        hdr = GradientFrame(self.window, TM.get('header_grad1','#0d0d2e'), TM.get('header_grad2','#001a1a'), height=60)
        hdr.place(x=0, y=0, relwidth=1)
        def draw_hdr(e, h=hdr):
            h._on_resize(e); h.delete('widgets')
            h.create_text(e.width//2, 30,
                text="👥   REGISTERED STUDENTS",
                font=("Inter 18pt", 17, "bold"),
                fill='#00E5CC', tags='widgets')
        hdr.bind('<Configure>', draw_hdr)
        tk.Frame(self.window, bg='#00E5CC', height=2).place(x=0, y=60, relwidth=1)

        # ── Semester selector bar ─────────────────────────────────────────────
        sem_bar = tk.Frame(self.window, bg='#080814', height=52)
        sem_bar.place(x=0, y=62, relwidth=1)
        tk.Label(sem_bar, text="Semester:",
                 font=("Inter 18pt", 10, "bold"),
                 bg='#080814', fg=TM.get('accent2','#7ecdc4')).place(x=14, y=14)

        self._sem_btns = []
        for i in range(1, 9):
            b = tk.Button(sem_bar, text=str(i),
                          font=("Inter 18pt", 10, "bold"),
                          width=3, relief=tk.FLAT, cursor='hand2',
                          command=lambda s=i: self._select_sem(s))
            b.place(x=105 + (i-1)*52, y=10, height=32)
            self._sem_btns.append(b)
        self._refresh_sem_btns()

        # Action buttons right side
        self.del_btn = GradientButton(sem_bar,
            text="🗑  Delete Selected",
            color1='#8B2500', color2='#5a1800',
            hover_color1='#E67E22', hover_color2='#C0392B',
            font=("Inter 18pt", 9, "bold"),
            width=150, height=34,
            command=self._delete_selected)
        self.del_btn.place(relx=1.0, x=-320, y=9)

        self.clr_btn = GradientButton(sem_bar,
            text="🗑  Clear Semester",
            color1='#6b0000', color2='#4a0000',
            hover_color1='#E74C3C', hover_color2='#C0392B',
            font=("Inter 18pt", 9, "bold"),
            width=150, height=34,
            command=self._clear_semester)
        self.clr_btn.place(relx=1.0, x=-162, y=9)

        tk.Frame(self.window, bg='#1a1a3e', height=1).place(x=0, y=114, relwidth=1)

        # ── Summary bar ───────────────────────────────────────────────────────
        self.sum_bar = GradientFrame(self.window, TM.get('header_grad1','#0d0d2e'), TM.get('header_grad2','#001a1a'), height=32)
        self.sum_bar.place(x=0, y=115, relwidth=1)
        self._sum_text = "Select a semester to view students"
        def draw_sum(e, sb=self.sum_bar):
            sb._on_resize(e); sb.delete('widgets')
            sb.create_text(e.width//2, 16,
                text=self._sum_text,
                font=("Roboto", 9), fill='#7ecdc4', tags='widgets')
        self.sum_bar.bind('<Configure>', draw_sum)
        self._draw_sum = draw_sum

        # Hint
        tk.Label(self.window,
                 text="💡  Click row to select  |  Double-click to view attendance history",
                 font=("Roboto", 8, "italic"),
                 bg=TM.get('bg','#0d0d1a'), fg='#444466').place(x=14, y=150)

        # ── Table ─────────────────────────────────────────────────────────────
        tbl_frame = tk.Frame(self.window, bg='#0a0a14')
        tbl_frame.place(x=0, y=168, relwidth=1, relheight=1, height=-168)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('RS.Treeview',
            background='#0d0d1a', foreground='white',
            fieldbackground='#0d0d1a',
            rowheight=28, font=('Roboto', 10))
        style.configure('RS.Treeview.Heading',
            background=TM.get('header_grad1','#0d0d2e'), foreground='#00E5CC',
            font=('Inter 18pt', 10, 'bold'), relief='flat')
        style.map('RS.Treeview',
            background=[('selected', '#1a3a6b')],
            foreground=[('selected', 'white')])

        vsb = tk.Scrollbar(tbl_frame, orient=tk.VERTICAL,
                            bg=TM.get('entry_bg','#1a1a2e'), troughcolor='#0d0d1a')
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb = tk.Scrollbar(tbl_frame, orient=tk.HORIZONTAL,
                            bg=TM.get('entry_bg','#1a1a2e'), troughcolor='#0d0d1a')
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # Columns: Roll | Name | Father | Reg No | Semester | Face | Fingerprint
        cols = ('Roll', 'Name', 'Father', 'Reg No', 'Semester', 'Face', 'Fingerprint')
        self.tree = ttk.Treeview(tbl_frame, columns=cols, show='headings',
                                  yscrollcommand=vsb.set,
                                  xscrollcommand=hsb.set,
                                  style='RS.Treeview')
        self.tree.pack(fill=tk.BOTH, expand=True)
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        cfg = {
            'Roll':        (140, 'center'),
            'Name':        (220, 'w'),
            'Father':      (200, 'w'),
            'Reg No':      (160, 'center'),
            'Semester':    (90,  'center'),
            'Face':        (110, 'center'),
            'Fingerprint': (120, 'center'),
        }
        for col, (w, a) in cfg.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor=a, minwidth=60)

        # Row tags
        self.tree.tag_configure('odd',  background='#0d0d1a', foreground='white')
        self.tree.tag_configure('even', background='#111128', foreground='white')

        self.tree.bind('<ButtonRelease-1>', self._on_click)
        self.tree.bind('<Double-Button-1>', self._on_dblclick)

    # ── Semester selector ─────────────────────────────────────────────────────

    def _refresh_sem_btns(self):
        for idx, b in enumerate(self._sem_btns):
            active = (idx + 1 == self.current_semester)
            b.config(bg='#00E5CC' if active else '#1a1a2e',
                     fg='#0d0d1a' if active else '#7ecdc4')

    def _select_sem(self, sem):
        self.current_semester = sem
        self._selected_iid    = None
        self._refresh_sem_btns()
        self._load(sem)

    # ── Load data ─────────────────────────────────────────────────────────────

    def _load(self, sem):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._selected_iid = None

        students = self.db.get_students_by_semester(sem)

        for idx, s in enumerate(students):
            # s: id, name, father, roll, reg, semester, image_path, created_at, auth_method
            s_id     = s[0]
            name     = s[1]
            father   = s[2]
            roll     = s[3]
            reg      = s[4]
            semester = s[5]
            img_path = s[6]
            method   = s[8] if len(s) > 8 else 'face'

            # Face column
            if method in ('face', 'both'):
                face_val = "✅  Registered" if os.path.exists(img_path) else "⚠  Missing"
            else:
                face_val = "—"

            # Fingerprint column
            fp_val = "✅  Registered" if method in ('fingerprint', 'both') else "—"

            tag = 'even' if idx % 2 == 0 else 'odd'
            self.tree.insert('', tk.END,
                values=(roll, name, father, reg, semester, face_val, fp_val),
                iid=str(s_id), tags=(tag,))

        # Summary
        n = len(students)
        face_count = sum(1 for s in students
                         if (s[8] if len(s)>8 else 'face') in ('face', 'both'))
        fp_count   = sum(1 for s in students
                         if (s[8] if len(s)>8 else 'face') in ('fingerprint', 'both'))

        self._sum_text = (
            f"Semester {sem}  |  "
            f"Total: {n}  |  "
            f"Face: {face_count}  |  "
            f"Fingerprint: {fp_count}"
        )
        w = self.sum_bar.winfo_width()
        h = self.sum_bar.winfo_height()
        if w > 1:
            e = type('E', (), {'width': w, 'height': h})()
            self._draw_sum(e)

    # ── Clicks ────────────────────────────────────────────────────────────────

    def _on_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid: return
        if iid == self._selected_iid:
            self.tree.selection_remove(iid)
            self._selected_iid = None
        else:
            self.tree.selection_set(iid)
            self._selected_iid = iid

    def _on_dblclick(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid: return
        values = self.tree.item(iid)['values']
        # values: roll, name, father, reg, semester, face, fp
        roll = values[0]
        name = values[1]
        self._open_history(int(iid), name, roll)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Nothing Selected",
                "Click a student row first."); return
        vals = self.tree.item(sel[0])['values']
        name = vals[1]; roll = vals[0]
        if not messagebox.askyesno("Confirm Delete",
            f"Delete student:\n{name}  (Roll: {roll})\n\n"
            "This will also delete their attendance records!"):
            return
        sid = int(sel[0])
        # Delete image
        s = self.db.get_student_by_id(sid)
        if s and os.path.exists(s[6]):
            try: os.remove(s[6])
            except: pass
        self.db.delete_student(sid)
        self._load(self.current_semester)

    def _clear_semester(self):
        sem = self.current_semester
        students = self.db.get_students_by_semester(sem)
        if not students:
            messagebox.showinfo("Empty",
                f"No students in Semester {sem}."); return
        if not messagebox.askyesno("Confirm Clear",
            f"Delete ALL {len(students)} students in Semester {sem}?\n"
            "This cannot be undone!"):
            return
        for s in students:
            if os.path.exists(s[6]):
                try: os.remove(s[6])
                except: pass
            self.db.delete_student(s[0])
        self._load(sem)

    # ── History popup ─────────────────────────────────────────────────────────

    def _open_history(self, student_id, name, roll):
        win = tk.Toplevel(self.window)
        win.title(f"Attendance — {name}")
        win.configure(bg=TM.get('bg','#0d0d1a'))
        win.transient(self.window)
        sw = win.winfo_screenwidth(); sh = win.winfo_screenheight()
        W2, H2 = 680, 520
        win.geometry(f"{W2}x{H2}+{(sw-W2)//2}+{(sh-H2)//2}")

        # Header
        hdr = GradientFrame(win, TM.get('header_grad1','#0d0d2e'), TM.get('header_grad2','#001a1a'), height=52)
        hdr.place(x=0, y=0, relwidth=1)
        def dh(e, h=hdr):
            h._on_resize(e); h.delete('w')
            h.create_text(e.width//2, 26,
                text=f"📋  {name}  |  Roll: {roll}",
                font=("Inter 18pt", 12, "bold"),
                fill='#00E5CC', tags='w')
        hdr.bind('<Configure>', dh)
        tk.Frame(win, bg='#00E5CC', height=2).place(x=0, y=52, relwidth=1)

        # Table
        fr = tk.Frame(win, bg='#0a0a14')
        fr.place(x=0, y=54, relwidth=1, relheight=1, height=-54)

        sv = tk.Scrollbar(fr, orient=tk.VERTICAL)
        sv.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.configure('H.Treeview',
            background='#0d0d1a', foreground='white',
            fieldbackground='#0d0d1a', rowheight=24,
            font=('Roboto', 10))
        style.configure('H.Treeview.Heading',
            background=TM.get('header_grad1','#0d0d2e'), foreground='#00E5CC',
            font=('Inter 18pt', 10, 'bold'), relief='flat')

        hcols = ('Date', 'Time', 'Status', 'Method')
        ht = ttk.Treeview(fr, columns=hcols, show='headings',
                           yscrollcommand=sv.set, style='H.Treeview')
        ht.pack(fill=tk.BOTH, expand=True)
        sv.config(command=ht.yview)

        for col, w in [('Date',90),('Time',80),('Status',90),('Method',100)]:
            ht.heading(col, text=col)
            ht.column(col, width=w, anchor='center')

        ht.tag_configure('P', foreground='#27ae60')
        ht.tag_configure('A', foreground='#e74c3c')

        records = self.db.get_student_attendance(student_id)
        for r in records:
            status = r[6] if len(r) > 6 else 'Present'
            tag    = 'P' if status == 'Present' else 'A'
            ht.insert('', tk.END,
                values=(r[4], r[5], status, r[7] if len(r)>7 else '—'),
                tags=(tag,))

        if not records:
            ht.insert('', tk.END,
                values=("No records", "—", "—", "—"))