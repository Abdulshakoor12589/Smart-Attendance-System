# fonts.py - Use system-installed Inter and Roboto fonts
import sys
import os

def setup():
    """Nothing to download - fonts are installed on Windows system."""
    return True

# ── Use these exact names as detected by tkinter ─────────────────────────────
INTER  = "Inter 18pt"        # headings, titles, buttons
ROBOTO = "Roboto"            # body text, labels, entries