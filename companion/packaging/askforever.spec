# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

package_dir = os.path.abspath(SPECPATH)
if not os.path.isdir(package_dir):
    package_dir = os.path.dirname(package_dir)
companion_dir = os.path.dirname(package_dir)

launcher = os.path.join(package_dir, 'launcher.py')
icon = os.path.join(package_dir, 'askforever.ico')

# Solo datos de ejecución del paquete; no se incluye addon/ ni dev/.
datas = collect_data_files('askforever')
hiddenimports = collect_submodules('askforever')
hiddenimports += ['keyring.backends.Windows', 'win32ctypes.core']

a = Analysis(
    [launcher],
    pathex=[companion_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AskForever',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AskForever',
)
