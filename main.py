# main.py - Entry point with splash screen
import tkinter as tk
import sys
import os
import threading

print(">>> Starting Smart Attendance System...")

os.makedirs("students", exist_ok=True)
os.makedirs("attendance_reports", exist_ok=True)


class SplashScreen:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Loading...")
        self.root.overrideredirect(True)
        self.root.configure(bg='#0d0d1a')
        self.root.attributes('-topmost', True)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        W, H = 480, 300
        self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

        self._running   = True
        self._dot_count = 0
        self._after_id  = None
        self._on_done   = None

        self._build()

    def _build(self):
        border = tk.Frame(self.root, bg='#00E5CC', padx=2, pady=2)
        border.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(border, bg='#0d0d1a')
        inner.pack(fill=tk.BOTH, expand=True)

        # Try favicon
        try:
            from PIL import Image, ImageTk
            base = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
            p = os.path.join(base, "favicon.png")
            if os.path.exists(p):
                img = Image.open(p).resize((70, 70), Image.Resampling.LANCZOS)
                self._ico = ImageTk.PhotoImage(img)
                tk.Label(inner, image=self._ico,
                         bg='#0d0d1a').pack(pady=(20, 0))
        except:
            tk.Label(inner, text="🎓", font=("Helvetica", 40),
                     bg='#0d0d1a', fg='#00E5CC').pack(pady=(20, 0))

        tk.Label(inner, text="SMART ATTENDANCE SYSTEM",
                 font=("Helvetica", 14, "bold"),
                 bg='#0d0d1a', fg='#00E5CC').pack(pady=(10, 2))

        tk.Label(inner, text="Efficient. Secure. Automated.",
                 font=("Helvetica", 9, "italic"),
                 bg='#0d0d1a', fg='#7ecdc4').pack()

        tk.Frame(inner, bg='#1a1a3e', height=1).pack(
            fill=tk.X, padx=40, pady=10)

        self.status_lbl = tk.Label(inner,
            text="Loading face recognition engine...",
            font=("Helvetica", 10),
            bg='#0d0d1a', fg='#aaaaaa')
        self.status_lbl.pack()

        self.dots_lbl = tk.Label(inner, text="●  ○  ○",
            font=("Helvetica", 12),
            bg='#0d0d1a', fg='#00E5CC')
        self.dots_lbl.pack(pady=(6, 0))

        tk.Label(inner,
            text="This may take up to 60 seconds on first load",
            font=("Helvetica", 8),
            bg='#0d0d1a', fg='#555577').pack(pady=(8, 0))

    def _animate(self):
        if not self._running:
            return
        dots = ["●  ○  ○", "●  ●  ○", "●  ●  ●",
                "○  ●  ●", "○  ○  ●", "○  ○  ○"]
        try:
            self.dots_lbl.config(
                text=dots[self._dot_count % len(dots)])
            self._dot_count += 1
            self._after_id = self.root.after(300, self._animate)
        except:
            pass

    def _set_status(self, text):
        try:
            self.status_lbl.config(text=text)
            self.root.update()
        except:
            pass

    def _finish(self):
        # Cancel pending after call first
        self._running = False
        if self._after_id:
            try:
                self.root.after_cancel(self._after_id)
            except:
                pass
        try:
            self.root.destroy()
        except:
            pass
        if self._on_done:
            self._on_done()

    def run(self, on_done):
        self._on_done = on_done
        self._animate()

        def load_in_bg():
            try:
                self.root.after(0, lambda: self._set_status(
                    "Loading face recognition engine..."))
                import face_recognition  # triggers dlib load
                self.root.after(0, lambda: self._set_status(
                    "✅  Ready! Opening login..."))
                self.root.after(600, self._finish)
            except Exception as e:
                self.root.after(0, lambda: self._set_status(
                    f"Warning: {e}"))
                self.root.after(1500, self._finish)

        t = threading.Thread(target=load_in_bg, daemon=True)
        t.start()
        self.root.mainloop()


def launch_main_app(admin_name):
    from main_dashboard import MainDashboard
    app = MainDashboard(admin_name)
    app.run()


def start_auth():
    from database import Database
    from auth import AuthWindow
    auth = AuthWindow(on_login_success=launch_main_app)
    auth.run()


if __name__ == "__main__":
    try:
        splash = SplashScreen()
        splash.run(on_done=start_auth)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")