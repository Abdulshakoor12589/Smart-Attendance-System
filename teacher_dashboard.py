# teacher_dashboard.py  — Semester → Class slots manager
import tkinter as tk
from tkinter import ttk, messagebox
import os, sys
from PIL import Image, ImageTk, ImageFilter, ImageEnhance
from database import Database
from gradient import GradientFrame, GradientButton
import theme as TM
import json


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
                win.iconphoto(False, img)
                win._icon_ref = img
            except: pass
            break


class TeacherDashboard:
    def __init__(self, parent, container=None):
        W, H = 1200, 760
        if container is not None:
            self.window = container
            self.standalone = False
        else:
            self.window = tk.Toplevel(parent)
            self.window.title("Teacher Dashboard — Class Setup")
            self.window.resizable(True, True)
            self.window.transient(parent)
            sw = self.window.winfo_screenwidth()
            sh = self.window.winfo_screenheight()
            W = min(1200, sw - 40)
            H = min(760,  sh - 40)
            self.window.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
            self.W, self.H = W, H
            _set_app_icon(self.window)
            self.standalone = True
        self.db      = Database()
        try:
            import json as _j
            _s = _j.load(open(os.path.join(get_base_dir(), "app_settings.json")))
            self._time_fmt = _s.get("time_format", "24h")
        except:
            self._time_fmt = "24h"
        self.sem     = tk.IntVar(value=1)
        self._refs   = {}
        self._cards  = {}   # slot -> card_frame

        self._build_ui()
        self._load_classes()
        if self.standalone: self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)

    # ── background ────────────────────────────────────────────────────────────

    def _draw_bg(self):
        w = self.window.winfo_width()  or self.W
        h = self.window.winfo_height() or self.H
        for name in ["tb.jpg", "tb.JPG"]:
            p = os.path.join(get_base_dir(), name)
            if os.path.exists(p):
                img = Image.open(p).resize((w, h), Image.Resampling.LANCZOS)
                img = ImageEnhance.Brightness(img).enhance(0.22)
                img = img.filter(ImageFilter.GaussianBlur(5))
                photo = ImageTk.PhotoImage(img)
                self._refs['bg'] = photo
                self.bg_cv.delete('bg')
                self.bg_cv.create_image(0, 0, image=photo, anchor='nw', tags='bg')
                self.bg_cv.tag_lower('bg')
                break

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.bg_cv = tk.Canvas(self.window, highlightthickness=0, bd=0)
        self.bg_cv.place(x=0, y=0, relwidth=1, relheight=1)
        self.window.bind('<Configure>',
            lambda e: self._draw_bg() if e.widget is self.window else None)
        self._draw_bg()

        # Header
        hdr = GradientFrame(self.window, TM.get('header_grad1','#0d0d2e'), TM.get('header_grad2','#001a1a'), height=58)
        hdr.place(x=0, y=0, relwidth=1)
        def dh(e, h=hdr):
            h._on_resize(e); h.delete('w')
            h.create_text(e.width//2, 29,
                text="🏫   TEACHER DASHBOARD  —  CLASS SETUP",
                font=("Inter 18pt", 16, "bold"),
                fill='#00E5CC', tags='w')
        hdr.bind('<Configure>', dh)
        tk.Frame(self.window, bg='#00E5CC', height=2).place(x=0, y=58, relwidth=1)

        # Semester bar
        sbar = tk.Frame(self.window, bg=TM.get('panel','#080814'), height=50)
        sbar.place(x=0, y=60, relwidth=1)
        tk.Label(sbar, text="Semester:",
                 font=("Inter 18pt", 10, "bold"),
                 bg=TM.get('panel','#080814'), fg=TM.get('accent2','#7ecdc4')).place(x=14, y=12)

        self._sem_btns = []
        for i in range(1, 9):
            b = tk.Button(sbar, text=str(i),
                          font=("Inter 18pt", 10, "bold"),
                          width=3, relief=tk.FLAT, cursor='hand2',
                          command=lambda s=i: self._select_sem(s))
            b.place(x=105 + (i-1)*52, y=9, height=32)
            self._sem_btns.append(b)
        self._refresh_sem_btns()

        tk.Frame(self.window, bg=TM.get('entry_border','#1a1a3e'), height=1).place(x=0, y=110, relwidth=1)

        # Info strip
        info = GradientFrame(self.window, TM.get('header_grad1','#0d0d2e'), TM.get('header_grad2','#001a1a'), height=30)
        info.place(x=0, y=111, relwidth=1)
        def di(e, f=info):
            f._on_resize(e); f.delete('w')
            f.create_text(e.width//2, 15,
                text="Click a class card to edit  |  Click  ✚ Add Class  to add  |  Max 8 classes per semester",
                font=("Roboto", 8), fill='#7ecdc4', tags='w')
        info.bind('<Configure>', di)

        # Cards area (scrollable)
        outer = tk.Frame(self.window, bg=TM.get('bg','#0d0d1a'))
        outer.place(x=0, y=141, relwidth=1, relheight=1, height=-141)

        self.cv = tk.Canvas(outer, bg=TM.get('bg','#0d0d1a'),
                             highlightthickness=0, bd=0)
        sb = tk.Scrollbar(outer, orient=tk.VERTICAL,
                           command=self.cv.yview,
                           bg=TM.get('entry_bg','#1a1a2e'), troughcolor='#0d0d1a')
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.cv.pack(fill=tk.BOTH, expand=True)
        self.cv.configure(yscrollcommand=sb.set)
        self.cv.bind('<MouseWheel>',
            lambda e: self.cv.yview_scroll(-1*(e.delta//120), 'units'))

        self.grid_frame = tk.Frame(self.cv, bg=TM.get('bg','#0d0d1a'))
        self.grid_win = self.cv.create_window(
            0, 0, anchor='nw', window=self.grid_frame)
        self.grid_frame.bind('<Configure>',
            lambda e: self.cv.configure(
                scrollregion=self.cv.bbox('all')))
        self.cv.bind('<Configure>',
            lambda e: self.cv.itemconfig(
                self.grid_win, width=e.width))

    # ── Semester ──────────────────────────────────────────────────────────────

    def _refresh_sem_btns(self):
        for i, b in enumerate(self._sem_btns):
            active = (i+1 == self.sem.get())
            b.config(bg='#00E5CC' if active else '#1a1a2e',
                     fg='#0d0d1a' if active else '#7ecdc4')

    def _select_sem(self, s):
        self.sem.set(s)
        self._refresh_sem_btns()
        self._load_classes()

    # ── Load & render cards ───────────────────────────────────────────────────

    def _load_classes(self):
        self._reload_time_fmt()   # refresh display format
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self._cards.clear()

        sem      = self.sem.get()
        existing = {r[2]: r for r in self.db.get_classes(sem)}
        # r: id,semester,slot,subject,teacher,time_start,time_end,created_at

        PAD  = 14
        COLS = 4

        # Only show filled slots + ONE empty "Add" card at the end
        # Max 8 total
        filled_slots = sorted(existing.keys())
        next_slot    = (max(filled_slots) + 1) if filled_slots else 1
        show_add     = next_slot <= 8   # still room to add

        slots_to_show = filled_slots + ([next_slot] if show_add else [])

        row = col = 0
        for slot in slots_to_show:
            data = existing.get(slot)
            card = self._make_card(self.grid_frame, slot, data)
            card.grid(row=row, column=col,
                      padx=PAD, pady=PAD, sticky='nsew')
            self._cards[slot] = card
            col += 1
            if col >= COLS:
                col = 0; row += 1

        for c in range(COLS):
            self.grid_frame.columnconfigure(c, weight=1)

    def _make_card(self, parent, slot, data):
        """Create one class card. data=None means empty slot."""
        filled = data is not None
        bg     = '#0d1a2e' if filled else '#0d0d1a'
        border = '#00E5CC' if filled else '#1a1a3e'

        outer = tk.Frame(parent, bg=border, bd=1)

        inner = tk.Frame(outer, bg=bg, cursor='hand2')
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Slot label
        slot_lbl = tk.Label(inner,
            text=f"Class {slot}",
            font=("Inter 18pt", 9, "bold"),
            bg=bg, fg=TM.get('accent','#00E5CC') if filled else '#333355')
        slot_lbl.pack(anchor='w', padx=10, pady=(8,0))

        if filled:
            subj = data[3]; teacher = data[4]
            t_start = data[5]; t_end = data[6]

            tk.Label(inner, text=subj,
                     font=("Inter 18pt", 12, "bold"),
                     bg=bg, fg='white',
                     wraplength=230).pack(anchor='w', padx=10, pady=(2,0))
            tk.Label(inner, text=f"👨‍🏫  {teacher}",
                     font=("Roboto", 9),
                     bg=bg, fg=TM.get('accent2','#7ecdc4')).pack(anchor='w', padx=10)
            def _fmt(t, fmt=self._time_fmt):
                try:
                    h, m = map(int, t.split(':'))
                    if fmt == '24h':
                        ap = 'AM' if h < 12 else 'PM'
                        return f"{h%12 or 12}:{m:02d} {ap}"
                    return t
                except: return t
            tk.Label(inner, text=f"🕐  {_fmt(t_start)}  →  {_fmt(t_end)}",
                     font=("Roboto", 9),
                     bg=bg, fg='#f39c12').pack(anchor='w', padx=10)

            btn_f = tk.Frame(inner, bg=bg)
            btn_f.pack(fill=tk.X, padx=8, pady=6)
            tk.Button(btn_f, text="✏  Edit",
                      font=("Roboto", 8, "bold"),
                      bg='#1a3a6b', fg='white', relief=tk.FLAT,
                      cursor='hand2', padx=8, pady=3,
                      command=lambda s=slot: self._edit_class(s)
                      ).pack(side=tk.LEFT, padx=(0,4))
            tk.Button(btn_f, text="🗑  Delete",
                      font=("Roboto", 8, "bold"),
                      bg='#6b1a1a', fg='white', relief=tk.FLAT,
                      cursor='hand2', padx=8, pady=3,
                      command=lambda s=slot: self._delete_class(s)
                      ).pack(side=tk.LEFT)
        else:
            tk.Label(inner, text="Empty",
                     font=("Roboto", 10),
                     bg=bg, fg='#333355').pack(expand=True)
            tk.Button(inner, text="✚  Add Class",
                      font=("Inter 18pt", 10, "bold"),
                      bg='#0d2a1a', fg=TM.get('accent','#00E5CC'),
                      relief=tk.FLAT, cursor='hand2',
                      pady=6,
                      command=lambda s=slot: self._edit_class(s)
                      ).pack(fill=tk.X, padx=10, pady=(0,10))

        return outer

    # ── Edit / Add dialog ─────────────────────────────────────────────────────

    def _reload_time_fmt(self):
        """Reload time format from app_settings.json each time dialog opens."""
        try:
            import json as _j
            _s = _j.load(open(os.path.join(get_base_dir(), "app_settings.json")))
            self._time_fmt = _s.get("time_format", "24h")
        except:
            self._time_fmt = "24h"

    def _edit_class(self, slot):
        self._reload_time_fmt()   # always use latest setting
        sem  = self.sem.get()
        rows = self.db.get_classes(sem)
        data = next((r for r in rows if r[2]==slot), None)

        dlg = tk.Toplevel(self.window)
        dlg.title(f"{'Edit' if data else 'Add'} Class {slot}  —  Semester {sem}")
        dlg.configure(bg=TM.get('bg','#0d0d1a'))
        dlg.resizable(False, False)
        dlg.transient(self.window)
        dlg.grab_set()
        W2,H2 = 420, 480
        sw = dlg.winfo_screenwidth(); sh = dlg.winfo_screenheight()
        dlg.geometry(f"{W2}x{H2}+{(sw-W2)//2}+{(sh-H2)//2}")

        hdr = GradientFrame(dlg, TM.get('header_grad1','#0d0d2e'), TM.get('header_grad2','#001a1a'), height=50)
        hdr.pack(fill=tk.X)
        def dh(e, h=hdr):
            h._on_resize(e); h.delete('w')
            h.create_text(e.width//2, 25,
                text=f"{'✏  Edit' if data else '✚  Add'}  Class {slot}  |  Sem {sem}",
                font=("Inter 18pt", 12, "bold"),
                fill='#00E5CC', tags='w')
        hdr.bind('<Configure>', dh)
        tk.Frame(dlg, bg='#00E5CC', height=2).pack(fill=tk.X)

        body = tk.Frame(dlg, bg=TM.get('bg','#0d0d1a'))
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        ent_kw = dict(font=("Roboto",10), bg=TM.get('entry_bg','#1a1a2e'), fg='white',
                      insertbackground='white', relief=tk.FLAT,
                      highlightthickness=1,
                      highlightbackground='#2a2a4e',
                      highlightcolor='#00E5CC')
        lbl_kw = dict(font=("Inter 18pt",9,"bold"),
                      bg=TM.get('bg','#0d0d1a'), fg=TM.get('accent','#00E5CC'))

        def lbl(t): tk.Label(body, text=t, **lbl_kw).pack(anchor='w', pady=(8,1))
        def ent(v=''):
            e = tk.Entry(body, **ent_kw)
            e.pack(fill=tk.X, ipady=6)
            if v: e.insert(0, v)
            return e

        lbl("Subject Name:")
        e_subj = ent(data[3] if data else '')

        lbl("Teacher Name:")
        e_tchr = ent(data[4] if data else '')

        # Time row with AM/PM
        lbl("Class Time:")

        def _parse_time_12(val):
            """Parse HH:MM (24h stored) → (HH, MM, AM/PM) for display."""
            try:
                h, m = map(int, val.split(':'))
                if self._time_fmt == '24h':
                    ampm = 'AM' if h < 12 else 'PM'
                    h12  = h % 12 or 12
                    return str(h12), f"{m:02d}", ampm
                else:
                    return f"{h:02d}", f"{m:02d}", ''
            except:
                return '8', '00', 'AM'

        def _to_24h(h_str, m_str, ampm):
            """Convert display values → HH:MM 24h for storage."""
            try:
                h = int(h_str); m = int(m_str)
                if self._time_fmt == '24h':
                    if ampm == 'PM' and h != 12: h += 12
                    if ampm == 'AM' and h == 12: h = 0
                return f"{h:02d}:{m:02d}"
            except:
                return "08:00"

        dd_kw = dict(font=("Roboto",9), bg=TM.get('entry_bg','#1a1a2e'), fg='white',
                     relief=tk.FLAT, highlightthickness=0,
                     activebackground='#2a2a4e')

        # ── From ──
        from_row = tk.Frame(body, bg=TM.get('bg','#0d0d1a'))
        from_row.pack(fill=tk.X, pady=(0,4))
        tk.Label(from_row, text="From:", **lbl_kw).pack(side=tk.LEFT, padx=(0,6))

        ts_h, ts_m, ts_ap = _parse_time_12(data[5] if data else '08:00')
        e_ts_h = tk.Entry(from_row, width=4, **ent_kw)
        e_ts_h.insert(0, ts_h)
        e_ts_h.pack(side=tk.LEFT, ipady=5)
        tk.Label(from_row, text=":", font=("Roboto",12,"bold"),
                 bg=TM.get('bg','#0d0d1a'), fg=TM.get('accent','#00E5CC')).pack(side=tk.LEFT)
        e_ts_m = tk.Entry(from_row, width=4, **ent_kw)
        e_ts_m.insert(0, ts_m)
        e_ts_m.pack(side=tk.LEFT, ipady=5, padx=(0,6))
        ts_ap_var = tk.StringVar(value=ts_ap)
        if self._time_fmt == '12h':
            ap_ts = tk.OptionMenu(from_row, ts_ap_var, 'AM', 'PM')
            ap_ts.config(**dd_kw, width=4); ap_ts.pack(side=tk.LEFT)

        # ── To ──
        to_row = tk.Frame(body, bg=TM.get('bg','#0d0d1a'))
        to_row.pack(fill=tk.X, pady=(4,4))
        tk.Label(to_row, text="To:", **lbl_kw).pack(side=tk.LEFT, padx=(0,6))

        te_h, te_m, te_ap = _parse_time_12(data[6] if data else '09:15')
        e_te_h = tk.Entry(to_row, width=4, **ent_kw)
        e_te_h.insert(0, te_h)
        e_te_h.pack(side=tk.LEFT, ipady=5)
        tk.Label(to_row, text=":", font=("Roboto",12,"bold"),
                 bg=TM.get('bg','#0d0d1a'), fg=TM.get('accent','#00E5CC')).pack(side=tk.LEFT)
        e_te_m = tk.Entry(to_row, width=4, **ent_kw)
        e_te_m.insert(0, te_m)
        e_te_m.pack(side=tk.LEFT, ipady=5, padx=(0,6))
        te_ap_var = tk.StringVar(value=te_ap)
        if self._time_fmt == '12h':
            ap_te = tk.OptionMenu(to_row, te_ap_var, 'AM', 'PM')
            ap_te.config(**dd_kw, width=4); ap_te.pack(side=tk.LEFT)

        fmt_hint = "HH:MM  AM/PM  e.g. 2:30 PM" if self._time_fmt == '12h' else "HH:MM  e.g. 08:00  14:30"
        tk.Label(body, text=f"Format: {fmt_hint}",
                 font=("Roboto",8), bg=TM.get('bg','#0d0d1a'), fg='#555577').pack(anchor='w')

        # Enter chaining
        e_subj.bind('<Return>', lambda e: e_tchr.focus_set())
        e_tchr.bind('<Return>', lambda e: e_ts_h.focus_set())
        e_ts_h.bind('<Return>', lambda e: e_ts_m.focus_set())
        e_ts_m.bind('<Return>', lambda e: e_te_h.focus_set())
        e_te_h.bind('<Return>', lambda e: e_te_m.focus_set())

        msg = tk.Label(body, text="", font=("Roboto",8),
                       bg=TM.get('bg','#0d0d1a'), fg='#e74c3c', wraplength=380)
        msg.pack(pady=4)

        def do_save():
            subj = e_subj.get().strip()
            tchr = e_tchr.get().strip()
            ts   = _to_24h(e_ts_h.get(), e_ts_m.get(), ts_ap_var.get())
            te   = _to_24h(e_te_h.get(), e_te_m.get(), te_ap_var.get())
            if not all([subj, tchr]):
                msg.config(text="⚠  Fill subject and teacher."); return
            try:
                sh, sm = map(int, ts.split(':'))
                eh, em = map(int, te.split(':'))
                if sh * 60 + sm >= eh * 60 + em:
                    msg.config(text="⚠  Start time must be before end time."); return
            except:
                msg.config(text="⚠  Invalid time values."); return
            ok, err = self.db.save_class(sem, slot, subj, tchr, ts, te)
            if ok:
                dlg.destroy()
                self._load_classes()
            else:
                msg.config(text=f"❌  {err}")

        e_te_m.bind('<Return>', lambda e: do_save())

        GradientButton(body, text="💾  Save Class",
            color1='#1a5a1a', color2='#0d3a0d',
            hover_color1='#27ae60', hover_color2='#1a8a4a',
            font=("Inter 18pt",11,"bold"),
            height=42, command=do_save).pack(fill=tk.X, pady=(8,4))

        tk.Button(body, text="Cancel",
                  font=("Roboto",9), relief=tk.FLAT,
                  bg=TM.get('entry_bg','#1a1a2e'), fg=TM.get('accent2','#7ecdc4'), cursor='hand2',
                  pady=4, command=dlg.destroy).pack(fill=tk.X)

    def _delete_class(self, slot):
        sem  = self.sem.get()
        rows = self.db.get_classes(sem)
        data = next((r for r in rows if r[2]==slot), None)
        if not data: return
        if not messagebox.askyesno("Delete Class",
            f"Delete:\n{data[3]} — {data[4]}\n"
            f"Time: {data[5]}–{data[6]}\n\nConfirm?"):
            return
        self.db.delete_class(sem, slot)
        self._load_classes()