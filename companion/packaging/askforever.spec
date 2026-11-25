# -*- mode: python ; coding: utf-8 -*-

import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

package_dir = os.path.abspath(SPECPATH)
if not os.path.isdir(package_dir):
    package_dir = os.path.dirname(package_dir)
companion_dir = os.path.dirname(package_dir)

launcher = os.path.join(package_dir, 'launcher.py')

# Solo datos de ejecución del paquete; no se incluye addon/ ni dev/.
datas = collect_data_files('askforever')
# keyring descubre sus backends por los metadatos del paquete.
datas += copy_metadata('keyring')
hiddenimports = collect_submodules('askforever')

if sys.platform == 'win32':
    icon = os.path.join(package_dir, 'askforever.ico')
    hiddenimports += ['keyring.backends.Windows', 'win32ctypes.core']
else:
    # En Linux el icono va en app/askforever.png y la clave se guarda en el
    # llavero del escritorio (Secret Service) a través de secretstorage/jeepney.
    icon = None
    hiddenimports += ['keyring.backends.SecretService', 'keyring.backends.chainer']
    hiddenimports += collect_submodules('secretstorage')
    hiddenimports += collect_submodules('jeepney')

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
    name='AskForeverApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
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
