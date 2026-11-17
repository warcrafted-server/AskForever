"""Windows notification-area icon implemented with the Win32 API."""

from __future__ import annotations

import ctypes
import os
import threading
from ctypes import wintypes
from pathlib import Path

WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_USER = 0x0400
WM_TRAY = WM_USER + 1
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_CONTEXTMENU = 0x007B
NIM_ADD = 0
NIM_MODIFY = 1
NIM_DELETE = 2
NIF_MESSAGE = 0x01
NIF_ICON = 0x02
NIF_TIP = 0x04
NIF_INFO = 0x10
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
IDI_APPLICATION = 32512
TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD = 0x0100
MF_STRING = 0x0000
MENU_OPEN = 1001
MENU_QUIT = 1002


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ('style', wintypes.UINT),
        ('lpfnWndProc', ctypes.c_void_p),
        ('cbClsExtra', ctypes.c_int),
        ('cbWndExtra', ctypes.c_int),
        ('hInstance', wintypes.HINSTANCE),
        ('hIcon', wintypes.HICON),
        ('hCursor', wintypes.HANDLE),
        ('hbrBackground', wintypes.HBRUSH),
        ('lpszMenuName', wintypes.LPCWSTR),
        ('lpszClassName', wintypes.LPCWSTR),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('hWnd', wintypes.HWND),
        ('uID', wintypes.UINT),
        ('uFlags', wintypes.UINT),
        ('uCallbackMessage', wintypes.UINT),
        ('hIcon', wintypes.HICON),
        ('szTip', wintypes.WCHAR * 128),
        ('dwState', wintypes.DWORD),
        ('dwStateMask', wintypes.DWORD),
        ('szInfo', wintypes.WCHAR * 256),
        ('uTimeoutOrVersion', wintypes.UINT),
        ('szInfoTitle', wintypes.WCHAR * 64),
        ('dwInfoFlags', wintypes.DWORD),
        ('guidItem', ctypes.c_byte * 16),
        ('hBalloonIcon', wintypes.HICON),
    ]


def notify_icon_data_size() -> int:
    return ctypes.sizeof(NOTIFYICONDATAW)


class TrayIcon:
    """Owns a hidden Win32 window and its notification-area icon."""

    def __init__(self, icon_path, on_open, on_exit, language='es',
                 tooltip='AskForever App'):
        self.icon_path = Path(icon_path)
        self.on_open = on_open
        self.on_exit = on_exit
        self.language = language
        self.tooltip = tooltip
        self._thread = None
        self._ready = threading.Event()
        self._started = False
        self._hwnd = None
        self._icon = None
        self._user32 = None
        self._kernel32 = None
        self._shell32 = None
        self._callback_type = None
        self._wndproc = None
        self._class_name = f'AskForeverTray{ id(self):x}'
        self._start_ok = False

    def start(self) -> bool:
        if self._started:
            return True
        if os.name != 'nt':
            return False
        self._started = True
        self._thread = threading.Thread(target=self._thread_main,
                                       name='AskForeverTray', daemon=True)
        self._thread.start()
        self._ready.wait(3.0)
        if not self._start_ok:
            self.remove()
        return self._start_ok

    def _thread_main(self):
        try:
            self._run_message_loop()
        except Exception:
            self._start_ok = False
            self._ready.set()

    def _run_message_loop(self):
        self._user32 = ctypes.WinDLL('user32', use_last_error=True)
        self._kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        self._shell32 = ctypes.WinDLL('shell32', use_last_error=True)
        self._configure_api_types()
        self._callback_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
            wintypes.WPARAM, wintypes.LPARAM)

        def window_proc(hwnd, message, wparam, lparam):
            if message == WM_TRAY:
                if lparam == WM_LBUTTONUP:
                    self.on_open()
                elif lparam in (WM_RBUTTONUP, WM_CONTEXTMENU):
                    self._show_menu(hwnd)
                return 0
            if message == WM_CLOSE:
                self._user32.DestroyWindow(hwnd)
                return 0
            if message == WM_DESTROY:
                self._user32.PostQuitMessage(0)
                return 0
            return self._user32.DefWindowProcW(hwnd, message, wparam, lparam)

        self._wndproc = self._callback_type(window_proc)
        instance = self._kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW()
        wc.lpfnWndProc = ctypes.cast(self._wndproc, ctypes.c_void_p)
        wc.hInstance = instance
        wc.lpszClassName = self._class_name
        if not self._user32.RegisterClassW(ctypes.byref(wc)):
            raise OSError(ctypes.get_last_error(), 'RegisterClassW failed')
        hwnd = self._user32.CreateWindowExW(
            0, self._class_name, '', 0, 0, 0, 0, 0,
            ctypes.c_void_p(-3), None, instance, None)
        if not hwnd:
            raise OSError(ctypes.get_last_error(), 'CreateWindowExW failed')
        self._hwnd = hwnd
        self._icon = self._load_icon(instance)
        data = self._new_data(NIF_ICON | NIF_MESSAGE | NIF_TIP)
        data.hIcon = self._icon
        data.uCallbackMessage = WM_TRAY
        data.szTip = self.tooltip[:127]
        self._start_ok = bool(self._shell32.Shell_NotifyIconW(NIM_ADD,
                                                              ctypes.byref(data)))
        self._ready.set()
        if not self._start_ok:
            self._user32.DestroyWindow(hwnd)
            return
        msg = wintypes.MSG()
        while True:
            result = self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result <= 0:
                break
            self._user32.TranslateMessage(ctypes.byref(msg))
            self._user32.DispatchMessageW(ctypes.byref(msg))
        if self._icon:
            self._user32.DestroyIcon(self._icon)
            self._icon = None

    def _configure_api_types(self):
        user32 = self._user32
        self._kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self._kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE
        user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
        user32.RegisterClassW.restype = wintypes.ATOM
        user32.CreateWindowExW.argtypes = [
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p,
        ]
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.DefWindowProcW.restype = ctypes.c_ssize_t
        user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT,
                                          wintypes.WPARAM, wintypes.LPARAM]
        user32.DestroyWindow.argtypes = [wintypes.HWND]
        user32.DestroyIcon.argtypes = [wintypes.HICON]
        user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR,
                                      wintypes.UINT, ctypes.c_int, ctypes.c_int,
                                      wintypes.UINT]
        user32.LoadImageW.restype = wintypes.HANDLE
        user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
        user32.LoadIconW.restype = wintypes.HICON
        user32.GetMessageW.restype = wintypes.BOOL
        user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                       wintypes.UINT, wintypes.UINT]
        user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        user32.CreatePopupMenu.restype = wintypes.HMENU
        user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT,
                                       wintypes.UINT, wintypes.LPCWSTR]
        user32.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT,
                                          ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                          wintypes.HWND, ctypes.c_void_p]
        user32.TrackPopupMenu.restype = wintypes.UINT
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.DestroyMenu.argtypes = [wintypes.HMENU]
        user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user32.PostQuitMessage.argtypes = [ctypes.c_int]
        user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT,
                                       wintypes.WPARAM, wintypes.LPARAM]
        self._shell32.Shell_NotifyIconW.argtypes = [
            wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
        self._shell32.Shell_NotifyIconW.restype = wintypes.BOOL

    def _load_icon(self, instance):
        icon = self._user32.LoadImageW(
            None, str(self.icon_path), IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
        if icon:
            return icon
        resource = ctypes.cast(ctypes.c_void_p(IDI_APPLICATION), wintypes.LPCWSTR)
        return self._user32.LoadIconW(None, resource)

    def _new_data(self, flags):
        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        data.hWnd = self._hwnd
        data.uID = 1
        data.uFlags = flags
        return data

    def _show_menu(self, hwnd):
        menu = self._user32.CreatePopupMenu()
        if not menu:
            return
        open_text, quit_text = (('Abrir', 'Salir') if self.language == 'es'
                                else ('Open', 'Quit'))
        self._user32.AppendMenuW(menu, MF_STRING, MENU_OPEN, open_text)
        self._user32.AppendMenuW(menu, MF_STRING, MENU_QUIT, quit_text)
        point = wintypes.POINT()
        self._user32.GetCursorPos(ctypes.byref(point))
        self._user32.SetForegroundWindow(hwnd)
        selected = self._user32.TrackPopupMenu(
            menu, TPM_RETURNCMD | TPM_RIGHTBUTTON, point.x, point.y, 0, hwnd, None)
        self._user32.DestroyMenu(menu)
        if selected == MENU_OPEN:
            self.on_open()
        elif selected == MENU_QUIT:
            self.on_exit()

    def show_balloon(self, title, text):
        if not self._start_ok or not self._hwnd:
            return False
        data = self._new_data(NIF_INFO)
        data.szInfoTitle = str(title)[:63]
        data.szInfo = str(text)[:255]
        data.dwInfoFlags = 0
        return bool(self._shell32.Shell_NotifyIconW(NIM_MODIFY,
                                                    ctypes.byref(data)))

    def remove(self):
        hwnd = self._hwnd
        if hwnd and self._shell32 is not None:
            try:
                data = self._new_data(0)
                self._shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(data))
            except Exception:
                pass
            try:
                self._user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            except Exception:
                pass
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._hwnd = None
        self._start_ok = False
