#!/usr/bin/env python3
"""Spike Linux: ventana tkinter siempre visible y transparente al ratón sobre WoW.

Dibuja un panel semitransparente arriba a la derecha durante 30 s. Comprueba
con WoW en ventana sin bordes que: (1) se ve encima del juego, (2) los clics
atraviesan el panel, (3) WoW no pierde el foco.

    python tools/spike_overlay_linux.py

Requisitos (Arch): tk (python tkinter), libxext. Corre bajo XWayland.
"""

from __future__ import annotations

import ctypes
import argparse
import ctypes.util
import tkinter as tk

DURATION_MS = 30_000
SHAPE_INPUT = 2
SHAPE_SET = 0


def click_through(window_ids: list[int]) -> bool:
    """Deja vacía la región de entrada (XShape) de cada ventana X y de sus padres."""
    x11 = ctypes.CDLL(ctypes.util.find_library('X11'))
    xext = ctypes.CDLL(ctypes.util.find_library('Xext'))
    x11.XOpenDisplay.restype = ctypes.c_void_p
    display = x11.XOpenDisplay(None)
    if not display:
        return False
    dpy = ctypes.c_void_p(display)
    x11.XQueryTree.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
                               ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_void_p),
                               ctypes.POINTER(ctypes.c_uint)]
    targets: list[int] = []
    for window in window_ids:
        while window and window not in targets:
            targets.append(window)
            root_id, parent = ctypes.c_ulong(), ctypes.c_ulong()
            children, count = ctypes.c_void_p(), ctypes.c_uint()
            if not x11.XQueryTree(dpy, window, ctypes.byref(root_id), ctypes.byref(parent),
                                  ctypes.byref(children), ctypes.byref(count)):
                break
            window = parent.value if parent.value != root_id.value else 0
    for window in targets:
        xext.XShapeCombineRectangles(dpy, ctypes.c_ulong(window), SHAPE_INPUT, 0, 0, None, 0,
                                     SHAPE_SET, 0)
    x11.XFlush(dpy)
    print('Ventanas X con entrada vacía:', [hex(w) for w in targets])
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--monitor-left', type=int, default=0, help='X del monitor donde está WoW')
    parser.add_argument('--monitor-width', type=int, default=1920, help='ancho de ese monitor')
    args = parser.parse_args()
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    try:
        root.attributes('-type', 'notification')
    except tk.TclError:
        pass
    root.attributes('-alpha', 0.85)
    root.configure(bg='#101820')
    width, height = 420, 90
    root.geometry(f'{width}x{height}+{args.monitor_left + args.monitor_width - width - 40}+40')
    tk.Label(root, text='AskForever: prueba de overlay\n¿Me ves sobre WoW? ¿Los clics pasan?',
             fg='#f0e6c8', bg='#101820', font=('sans', 12), justify='left').pack(padx=12, pady=12)
    root.update()
    ok = click_through([root.winfo_id(), int(root.wm_frame(), 16)])
    print('Click-through (XShape):', 'aplicado' if ok else 'NO aplicado (sin pantalla X)')
    root.after(DURATION_MS, root.destroy)
    root.mainloop()


if __name__ == '__main__':
    main()
