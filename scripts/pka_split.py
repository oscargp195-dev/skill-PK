#!/usr/bin/env python3
"""Separa / vuelve a unir la red del alumno (primer <PACKETTRACER5>) dentro del XML de un .pka/.pkt.

El XML completo de un .pka NO es XML válido (VARIABLE_MANAGER lleva bytes binarios), así que
no se puede parsear entero: se extrae solo el primer bloque <PACKETTRACER5>...</PACKETTRACER5>
(la red sobre la que trabaja el alumno), se edita, y se vuelve a insertar byte a byte.

Uso:
  python3 pka_split.py split completo.xml red.xml
  python3 pka_split.py merge completo.xml red_editada.xml salida.xml
"""
import re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows
except Exception:
    pass

OPEN = b"<PACKETTRACER5>"
CLOSE = b"</PACKETTRACER5>"


def bounds(full: bytes):
    a = full.find(OPEN)
    b = full.find(CLOSE, a)
    if a < 0 or b < 0:
        sys.exit("No se encontró <PACKETTRACER5>")
    return a, b + len(CLOSE)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    full = open(sys.argv[2], "rb").read()
    a, b = bounds(full)
    if cmd == "split":
        open(sys.argv[3], "wb").write(full[a:b])
        n = full.count(OPEN)
        print(f"OK: red extraída ({b - a} bytes). Bloques PACKETTRACER5 en el archivo: {n}")
    elif cmd == "merge":
        new = open(sys.argv[3], "rb").read()
        new = re.sub(rb"^\s*<\?xml[^>]*\?>\s*", b"", new)
        open(sys.argv[4], "wb").write(full[:a] + new.strip() + full[b:])
        print(f"OK -> {sys.argv[4]}")
    else:
        sys.exit(__doc__)
