# zk_finger.py — ZKTeco USB Fingerprint Scanner Integration
# Requires: ZKFinger SDK installed from https://www.zkteco.com
# DLL location: C:\Program Files\ZKFinger SDK\lib\x64\ZKFPLib.dll
import ctypes
import os
import sys

# ── Try to load ZKFinger DLL ──────────────────────────────────────────────────
ZKFP_DLL_PATHS = [
    r"C:\Program Files\ZKFinger SDK\lib\x64\ZKFPLib.dll",
    r"C:\Program Files (x86)\ZKFinger SDK\lib\x86\ZKFPLib.dll",
    r"C:\Program Files\ZKFinger SDK\lib\ZKFPLib.dll",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ZKFPLib.dll"),
]

_dll = None

def _load_dll():
    global _dll
    if _dll is not None:
        return _dll
    for path in ZKFP_DLL_PATHS:
        if os.path.exists(path):
            try:
                _dll = ctypes.WinDLL(path)
                return _dll
            except Exception:
                continue
    return None


# ── Constants ─────────────────────────────────────────────────────────────────
ZKFP_ERR_OK        = 0
ZKFP_ERR_INITLIB   = -1
ZKFP_ERR_NOTOPEN   = -2
ZKFP_ERR_ALREADY   = -10
TEMPLATE_SIZE      = 2048
IMAGE_WIDTH        = 300
IMAGE_HEIGHT       = 400


class ZKFinger:
    """ZKTeco fingerprint scanner wrapper."""

    def __init__(self):
        self._handle  = None
        self._dll     = None
        self.ready    = False
        self.last_err = ""

    def init(self):
        """Initialize ZKFinger SDK. Returns True if scanner found."""
        self._dll = _load_dll()
        if not self._dll:
            self.last_err = (
                "ZKFinger SDK not found.\n"
                "Download from zkteco.com and install ZKFinger SDK,\n"
                "then copy ZKFPLib.dll next to this app.")
            return False
        try:
            ret = self._dll.ZKFPM_Init()
            if ret != ZKFP_ERR_OK:
                self.last_err = f"SDK init failed (code {ret})"
                return False

            count = self._dll.ZKFPM_GetDeviceCount()
            if count <= 0:
                self.last_err = "No ZKTeco scanner found. Connect scanner and try again."
                return False

            handle = self._dll.ZKFPM_OpenDevice(0)
            if handle == 0:
                self.last_err = "Cannot open scanner. Try unplugging and reconnecting."
                return False

            self._handle = handle
            self.ready   = True
            return True
        except Exception as e:
            self.last_err = str(e)
            return False

    def close(self):
        try:
            if self._handle and self._dll:
                self._dll.ZKFPM_CloseDevice(self._handle)
            if self._dll:
                self._dll.ZKFPM_Terminate()
        except: pass
        self._handle = None
        self.ready   = False

    def capture(self):
        """
        Capture one fingerprint. Returns (template_bytes, image_bytes) or (None, None).
        Blocks until finger is placed or timeout.
        """
        if not self.ready or not self._handle:
            return None, None
        try:
            img_buf  = ctypes.create_string_buffer(IMAGE_WIDTH * IMAGE_HEIGHT)
            tmpl_buf = ctypes.create_string_buffer(TEMPLATE_SIZE)
            tmpl_len = ctypes.c_int(TEMPLATE_SIZE)
            img_w    = ctypes.c_int(IMAGE_WIDTH)
            img_h    = ctypes.c_int(IMAGE_HEIGHT)

            ret = self._dll.ZKFPM_AcquireFingerprint(
                self._handle,
                img_buf, ctypes.byref(img_w), ctypes.byref(img_h),
                tmpl_buf, ctypes.byref(tmpl_len))

            if ret == ZKFP_ERR_OK:
                template = bytes(tmpl_buf[:tmpl_len.value])
                image    = bytes(img_buf[:img_w.value * img_h.value])
                return template, image
            return None, None
        except Exception as e:
            self.last_err = str(e)
            return None, None

    def match(self, template1: bytes, template2: bytes) -> int:
        """
        Compare two templates. Returns match score (>= 50 = match).
        Returns -1 on error.
        """
        if not self._dll:
            return -1
        try:
            buf1 = ctypes.create_string_buffer(template1)
            buf2 = ctypes.create_string_buffer(template2)
            score = self._dll.ZKFPM_DBMatch(
                buf1, len(template1),
                buf2, len(template2))
            return score
        except:
            return -1

    def get_image_pil(self, image_bytes, width=IMAGE_WIDTH, height=IMAGE_HEIGHT):
        """Convert raw grayscale image bytes to PIL Image."""
        try:
            from PIL import Image
            import numpy as np
            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            arr = arr.reshape((height, width))
            return Image.fromarray(arr, mode='L').convert('RGB')
        except:
            return None


# ── Singleton ─────────────────────────────────────────────────────────────────
_scanner = None

def get_scanner() -> ZKFinger:
    global _scanner
    if _scanner is None:
        _scanner = ZKFinger()
    return _scanner

def is_available() -> bool:
    return _load_dll() is not None