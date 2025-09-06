# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(
	['app_launcher.py'],
	pathex=[],
	binaries=[],
	datas=[('streamlit_app.py', '.'), ('templates/*', 'templates')],
	hiddenimports=['streamlit', 'pandas', 'selenium', 'jinja2', 'openpyxl', 'openai', 'dotenv'],
	hookspath=[],
	runtime_hooks=[],
	excludes=[],
	cipher=block_cipher,
	noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
	pyz,
	a.scripts,
	a.binaries,
	a.zipfiles,
	a.datas,
	name='WebFormRPA',
	debug=False,
	strip=False,
	upx=True,
	console=True,
	disable_windowed_traceback=False,
	target_arch=None,
)
