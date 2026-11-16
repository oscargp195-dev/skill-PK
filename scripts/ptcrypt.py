#!/usr/bin/env python3
"""Cifra / descifra archivos de Cisco Packet Tracer 7+ (.pkt / .pka) <-> XML.

Uso:
  python3 ptcrypt.py d entrada.pka salida.xml   # descifrar
  python3 ptcrypt.py e entrada.xml salida.pka   # cifrar

Formato: XML -> [tamaño BE 4 bytes + zlib] -> XOR (len-i) -> Twofish-EAX
(clave 0x89*16, nonce 0x10*16, tag de 16 bytes al final) -> invertir + XOR (len - i*len).
"""
import os, sys, zlib, struct

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
try:  # extensión C (rápida) si hay binario para esta plataforma; si no, Python puro (Windows)
    from twofish import Twofish  # noqa: E402
except Exception:
    from twofish_py import Twofish  # noqa: E402

KEY = bytes([137] * 16)
IV = bytes([16] * 16)
_E = Twofish(KEY).encrypt


def _xor(a, b):
    n = min(len(a), len(b))
    return (int.from_bytes(a[:n], "big") ^ int.from_bytes(b[:n], "big")).to_bytes(n, "big")


def _dbl(b):
    n = int.from_bytes(b, "big") << 1
    if n >> 128:
        n = (n ^ 0x87) & ((1 << 128) - 1)
    return n.to_bytes(16, "big")


_L = _E(bytes(16))
_K1 = _dbl(_L)
_K2 = _dbl(_K1)


def _cmac(m):
    blocks = [m[i:i + 16] for i in range(0, len(m), 16)] or [b""]
    last = blocks[-1]
    if len(last) == 16:
        last = _xor(last, _K1)
    else:
        last = _xor(last + b"\x80" + bytes(15 - len(last)), _K2)
    blocks[-1] = last
    x = bytes(16)
    for b in blocks:
        x = _E(_xor(x, b))
    return x


def _omac(t, m):
    return _cmac(bytes(15) + bytes([t]) + m)


def _ctr(n, data):
    c = int.from_bytes(n, "big")
    out = bytearray()
    for i in range(0, len(data), 16):
        ks = _E(c.to_bytes(16, "big"))
        c = (c + 1) & ((1 << 128) - 1)
        out += _xor(data[i:i + 16], ks)
    return bytes(out)


def _eax_dec(ct):
    data, tag = ct[:-16], ct[-16:]
    n = _omac(0, IV)
    t = _xor(_xor(n, _omac(1, b"")), _omac(2, data))
    if t != tag:
        raise ValueError("Tag EAX incorrecto: el archivo no es un .pkt/.pka de PT 7+ o está dañado")
    return _ctr(n, data)


def _eax_enc(pt):
    n = _omac(0, IV)
    c = _ctr(n, pt)
    return c + _xor(_xor(n, _omac(1, b"")), _omac(2, c))


def decrypt(inp: bytes) -> bytes:
    n = len(inp)
    s1 = bytes(inp[n - 1 - i] ^ ((n - i * n) & 0xFF) for i in range(n))
    s2 = bytearray(_eax_dec(s1))
    m = len(s2)
    for i in range(m):
        s2[i] ^= (m - i) & 0xFF
    return zlib.decompress(bytes(s2[4:]))


def encrypt(xml: bytes) -> bytes:
    s = bytearray(struct.pack(">I", len(xml)) + zlib.compress(xml))
    m = len(s)
    for i in range(m):
        s[i] ^= (m - i) & 0xFF
    e = _eax_enc(bytes(s))
    n = len(e)
    out = bytearray(n)
    for i in range(n):
        out[n - 1 - i] = e[i] ^ ((n - i * n) & 0xFF)
    return bytes(out)


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] not in ("d", "e"):
        sys.exit(__doc__)
    mode, src, dst = sys.argv[1:]
    data = open(src, "rb").read()
    open(dst, "wb").write(decrypt(data) if mode == "d" else encrypt(data))
    print(f"OK -> {dst}")
