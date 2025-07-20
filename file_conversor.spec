# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Coletar módulos e dados do tkinter
tkinter_imports = collect_submodules('tkinter')

a = Analysis(
    ['file_conversor.py'],  # Arquivo principal
    pathex=[],
    binaries=[
        # Incluir FFmpeg (necessário para conversões)
        ('ffmpeg.exe', '.') if os.name == 'nt' else ('ffmpeg', '.'),
        # Se tiver ffprobe, inclua também
        ('ffprobe.exe', '.') if os.name == 'nt' and os.path.exists('ffprobe.exe') else None,
    ],
    datas=[
        # Incluir arquivos de dados do tkinter se necessário
        # *collect_data_files('tkinter', subdir='tkinter'),
    ],
    hiddenimports=[
        # Módulos tkinter
        *tkinter_imports,
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.ttk',
        'tkinter.font',
        
        # Módulos padrão do Python usados no código
        'os',
        'sys', 
        're',
        'threading',
        'subprocess',
        'logging',
        'pathlib',
        'time',
        'datetime',
        'shutil',
        
        # Módulos específicos que podem ser necessários
        '_tkinter',
        
        # Codecs e bibliotecas de sistema (caso necessário)
        'encodings',
        'encodings.utf_8',
        'encodings.cp1252',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Excluir módulos desnecessários para reduzir tamanho
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filtrar binários None
a.binaries = [x for x in a.binaries if x is not None]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Conversor Multimidia',  # Nome do executável
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # False para esconder o console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,  # Ícone opcional
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Conversor Multimidia',  # Nome da pasta da aplicação
)

# Configuração adicional para Windows
if os.name == 'nt':
    app = BUNDLE(
        coll,
        name='Conversor Multimidia.app',
        icon='icon.ico' if os.path.exists('icon.ico') else None,
        bundle_identifier=None,
    )