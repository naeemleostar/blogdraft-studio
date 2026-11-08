"""Writes version_info.txt for PyInstaller (shows name/version in Windows file properties)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import config  # noqa: E402

parts = [int(x) for x in config.APP_VERSION.split(".")] + [0, 0, 0]
v = tuple(parts[:4])
open("version_info.txt", "w", encoding="utf-8").write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={v}, prodvers={v}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName', 'BlogDraft Studio (open source)'),
    StringStruct('FileDescription', 'BlogDraft Studio - WordPress draft writer'),
    StringStruct('FileVersion', '{config.APP_VERSION}'),
    StringStruct('InternalName', 'BlogDraft Studio'),
    StringStruct('LegalCopyright', 'MIT License'),
    StringStruct('OriginalFilename', 'BlogDraft Studio.exe'),
    StringStruct('ProductName', 'BlogDraft Studio'),
    StringStruct('ProductVersion', '{config.APP_VERSION}')])]),
  VarFileInfo([VarStruct('Translation', [1033, 1200])])])
""")
print("version_info.txt for", config.APP_VERSION)
