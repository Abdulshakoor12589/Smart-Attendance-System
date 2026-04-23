# fp_session.py - Windows Hello permission once per session
import threading

_verified = False
_lock = threading.Lock()

def is_verified():
    return _verified

def set_verified(val):
    global _verified
    with _lock:
        _verified = val

def reset():
    """Call on logout."""
    global _verified
    with _lock:
        _verified = False