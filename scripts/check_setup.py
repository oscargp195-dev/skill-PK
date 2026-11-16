#!/usr/bin/env python3
"""Comprueba si este equipo tiene todo lo que necesita la skill packet-tracer-lab.

Uso: python check_setup.py
Sale con código 0 si todo lo IMPRESCINDIBLE está OK. Lo que falte se instala con
setup_windows.ps1 (Windows), SIEMPRE después de pedir permiso al alumno.
"""
import glob, os, platform, shutil, subprocess, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
WIN = platform.system() == "Windows"
HOME = os.path.expanduser("~")
results = []  # (estado, nombre, detalle)  estado: OK | FALTA | AVISO


def add(ok, name, detail="", required=True):
    results.append(("OK" if ok else ("FALTA" if required else "AVISO"), name, detail))


def run(cmd, timeout=60):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=WIN and isinstance(cmd, str))
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


# 1. Python
add(sys.version_info >= (3, 8), "Python >= 3.8", sys.version.split()[0])

# 2. Cifrado .pka (Twofish C o Python puro)
sys.path.insert(0, os.path.join(HERE, "lib"))
try:
    try:
        from twofish import Twofish  # noqa: F401
        backend = "extensión C"
    except Exception:
        from twofish_py import Twofish  # noqa: F401
        backend = "Python puro"
    ok = Twofish(bytes(16)).encrypt(bytes(16)).hex().upper() == "9F589F5CF6122C32B6BFEC2F2AE8C35A"
    add(ok, "Cifrado Twofish (.pka/.pkt)", backend)
except Exception as e:  # noqa: BLE001
    add(False, "Cifrado Twofish (.pka/.pkt)", str(e))

# 3. lxml (opcional: conserva CDATA; sin él funciona con ElementTree)
try:
    import lxml  # noqa: F401
    add(True, "lxml (opcional)", "instalado", required=False)
except ImportError:
    add(False, "lxml (opcional)", "no instalado: funciona igual con ElementTree", required=False)

# 4. uv / uvx (lanza el MCP packet-tracer-mcp)
uvx = shutil.which("uvx") or (os.path.join(HOME, ".local", "bin", "uvx.exe") if WIN else None)
add(bool(uvx and os.path.exists(uvx)), "uv / uvx", uvx or "no encontrado")

# 5. MCP registrado en Claude Code
claude = shutil.which("claude")
if claude:
    rc, out = run([claude, "mcp", "list"] if not WIN else "claude mcp list", timeout=90)
    reg = "packet-tracer" in out
    add(reg, "MCP packet-tracer registrado en Claude Code",
        ("conectado" if "Connected" in out.split("packet-tracer", 1)[-1][:200] else "registrado") if reg else "no registrado")
else:
    add(False, "MCP packet-tracer registrado en Claude Code", "no se encontró el comando 'claude' (¿otro agente?)", required=False)

# 6. Skill del MCP (guía de las herramientas pt_*)
skill_dirs = [os.path.join(HOME, ".claude", "skills", "packet-tracer"),
              os.path.join(HOME, ".agents", "skills", "packet-tracer")]
add(any(os.path.exists(os.path.join(d, "SKILL.md")) for d in skill_dirs),
    "Skill 'packet-tracer' del MCP", "", required=False)

# 7. Cisco Packet Tracer y su extensión MCP
if WIN:
    pt_dirs = [d for pat in (r"C:\Program Files\Cisco Packet Tracer*", r"C:\Program Files (x86)\Cisco Packet Tracer*")
               for d in glob.glob(pat)]
else:
    pt_dirs = [d for d in ("/opt/pt", "/opt/packettracer", "/Applications/Cisco Packet Tracer") if os.path.isdir(d)]
add(bool(pt_dirs), "Cisco Packet Tracer instalado", "; ".join(pt_dirs) or "no encontrado (se instala a mano con la cuenta NetAcad)")
pts = [p for d in pt_dirs for p in glob.glob(os.path.join(d, "extensions", "**", "*.pts"), recursive=True)
       if "mcp" in os.path.basename(p).lower()]
pts += glob.glob(os.path.join(HOME, "Downloads", "MCP*Control*Center*.pts")) + \
    glob.glob(os.path.join(HOME, "Descargas", "MCP*Control*Center*.pts"))
add(bool(pts), "Extensión MCP-Control-Center.pts", "; ".join(pts) or "no encontrada", required=False)

w = max(len(n) for _, n, _ in results)
for st, n, d in results:
    print(f"[{st:5}] {n.ljust(w)}  {d}")
missing = [n for st, n, _ in results if st == "FALTA"]
print()
if missing:
    print("FALTA:", ", ".join(missing))
    print("Pide permiso al alumno y ejecuta: powershell -ExecutionPolicy Bypass -File setup_windows.ps1" if WIN
          else "Instálalo con el gestor de paquetes del sistema (ver README).")
    sys.exit(1)
print("Todo lo imprescindible está OK.")
