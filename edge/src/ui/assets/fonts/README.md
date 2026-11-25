# Inter desktop fonts

Unmodified static Inter Regular and Bold from the official Inter 4.1 release:
https://github.com/rsms/inter/releases/tag/v4.1

Copyright and SIL Open Font License 1.1 terms are included in LICENSE.txt.
The OvaLens application code remains Apache-2.0 licensed.

These two TrueType files total 832,068 bytes and include the peso symbol.
`desktop_style.py` registers them for the application process before creating Tk.
There is no runtime download or system-wide font installation. Windows uses
private GDI registration; Linux uses Fontconfig application fonts. If registration
is unavailable, the app logs the fallback and uses Segoe UI or DejaVu Sans.
