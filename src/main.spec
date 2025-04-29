# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('vasoanalyzer/VasoAnalyzer Splash Screen.png', 'VasoAnalyzer Splash Screen.png'),
        ('vasoanalyzer/VasoAnalyzerIcon.icns', 'VasoAnalyzerIcon.icns'),
        ('vasoanalyzer/', 'vasoanalyzer'),
        ('/Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/site-packages/matplotlib/mpl-data', 'matplotlib/mpl-data'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VasoAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='vasoanalyzer/VasoAnalyzerIcon.icns'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VasoAnalyzer'
)

app = BUNDLE(
    coll,
    name='VasoAnalyzer 2.0.app',
    icon='vasoanalyzer/VasoAnalyzerIcon.icns',
    bundle_identifier='com.tykockilab.vasoanalyzer2'
)