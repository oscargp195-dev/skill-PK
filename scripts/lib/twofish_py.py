"""Twofish (cifrado de bloque de 128 bits) en Python puro, sin dependencias.

Sustituye a la extensión C (_twofish*.so) en Windows/macOS o donde no haya binario.
Solo hace falta encrypt() (EAX usa el cifrado en modo CTR/CMAC), pero se incluye decrypt().
Claves de 16, 24 o 32 bytes. Referencia: Schneier et al., "Twofish: A 128-Bit Block Cipher".
"""

_Q0_T = (
    (0x8, 0x1, 0x7, 0xD, 0x6, 0xF, 0x3, 0x2, 0x0, 0xB, 0x5, 0x9, 0xE, 0xC, 0xA, 0x4),
    (0xE, 0xC, 0xB, 0x8, 0x1, 0x2, 0x3, 0x5, 0xF, 0x4, 0xA, 0x6, 0x7, 0x0, 0x9, 0xD),
    (0xB, 0xA, 0x5, 0xE, 0x6, 0xD, 0x9, 0x0, 0xC, 0x8, 0xF, 0x3, 0x2, 0x4, 0x7, 0x1),
    (0xD, 0x7, 0xF, 0x4, 0x1, 0x2, 0x6, 0xE, 0x9, 0xB, 0x3, 0x0, 0x8, 0x5, 0xC, 0xA),
)
_Q1_T = (
    (0x2, 0x8, 0xB, 0xD, 0xF, 0x7, 0x6, 0xE, 0x3, 0x1, 0x9, 0x4, 0x0, 0xA, 0xC, 0x5),
    (0x1, 0xE, 0x2, 0xB, 0x4, 0xC, 0x3, 0x7, 0x6, 0xD, 0xA, 0x5, 0xF, 0x9, 0x0, 0x8),
    (0x4, 0xC, 0x7, 0x5, 0x1, 0x6, 0x9, 0xA, 0x0, 0xE, 0xD, 0x8, 0x2, 0xB, 0x3, 0xF),
    (0xB, 0x9, 0x5, 0x1, 0xC, 0x3, 0xD, 0xE, 0x6, 0x4, 0x7, 0xF, 0x2, 0x0, 0x8, 0xA),
)


def _ror4(x, n):
    return ((x >> n) | (x << (4 - n))) & 0xF


def _make_q(t):
    out = []
    for x in range(256):
        a0, b0 = x >> 4, x & 0xF
        a1 = a0 ^ b0
        b1 = a0 ^ _ror4(b0, 1) ^ ((8 * a0) & 0xF)
        a2, b2 = t[0][a1], t[1][b1]
        a3 = a2 ^ b2
        b3 = a2 ^ _ror4(b2, 1) ^ ((8 * a2) & 0xF)
        a4, b4 = t[2][a3], t[3][b3]
        out.append((b4 << 4) | a4)
    return out


Q0 = _make_q(_Q0_T)
Q1 = _make_q(_Q1_T)


def _gf_mul(a, b, poly):
    r = 0
    while b:
        if b & 1:
            r ^= a
        a <<= 1
        if a & 0x100:
            a ^= poly
        b >>= 1
    return r


_MDS = ((0x01, 0xEF, 0x5B, 0x5B), (0x5B, 0xEF, 0xEF, 0x01),
        (0xEF, 0x5B, 0x01, 0xEF), (0xEF, 0x01, 0xEF, 0x5B))
_RS = ((0x01, 0xA4, 0x55, 0x87, 0x5A, 0x58, 0xDB, 0x9E),
       (0xA4, 0x56, 0x82, 0xF3, 0x1E, 0xC6, 0x68, 0xE5),
       (0x02, 0xA1, 0xFC, 0xC1, 0x47, 0xAE, 0x3D, 0x19),
       (0xA4, 0x55, 0x87, 0x5A, 0x58, 0xDB, 0x9E, 0x03))
M32 = 0xFFFFFFFF


def _rol(x, n):
    return ((x << n) | (x >> (32 - n))) & M32


def _ror(x, n):
    return ((x >> n) | (x << (32 - n))) & M32


def _mds_col(col, y):
    """Contribución de un byte y (posición col) al producto MDS, como palabra de 32 bits."""
    return sum(_gf_mul(_MDS[row][col], y, 0x169) << (8 * row) for row in range(4))


# orden de las cajas q por byte y por etapa (k = 4 .. 1), según la especificación
_QORD = (
    (Q1, Q0, Q0, Q1),  # etapa k=4  (byte 0..3)
    (Q1, Q1, Q0, Q0),  # etapa k=3
    (Q0, Q1, Q0, Q1),  # etapa k=2 (primer xor)
    (Q0, Q0, Q1, Q1),  # etapa k=2 (segundo xor)
    (Q1, Q0, Q1, Q0),  # salida final
)


def _h_byte(i, x, L):
    """Camino de un byte por h(): L = lista de palabras (L0..Lk-1)."""
    k = len(L)
    b = lambda w: (w >> (8 * i)) & 0xFF  # noqa: E731
    if k == 4:
        x = _QORD[0][i][x] ^ b(L[3])
    if k >= 3:
        x = _QORD[1][i][x] ^ b(L[2])
    x = _QORD[2][i][x] ^ b(L[1])
    x = _QORD[3][i][x] ^ b(L[0])
    return _QORD[4][i][x]


def _h(X, L):
    return (_mds_col(0, _h_byte(0, X & 0xFF, L)) ^ _mds_col(1, _h_byte(1, (X >> 8) & 0xFF, L)) ^
            _mds_col(2, _h_byte(2, (X >> 16) & 0xFF, L)) ^ _mds_col(3, _h_byte(3, X >> 24, L)))


class Twofish:
    def __init__(self, key):
        if not isinstance(key, (bytes, bytearray)) or not 0 < len(key) <= 32:
            raise ValueError("invalid key length")
        n = 16 if len(key) <= 16 else 24 if len(key) <= 24 else 32
        key = bytes(key) + bytes(n - len(key))
        k = n // 8
        M = [int.from_bytes(key[4 * i:4 * i + 4], "little") for i in range(2 * k)]
        Me, Mo = M[0::2], M[1::2]
        S = []
        for i in range(k):
            m = key[8 * i:8 * i + 8]
            s = [0] * 4
            for r in range(4):
                v = 0
                for c in range(8):
                    v ^= _gf_mul(_RS[r][c], m[c], 0x14D)
                s[r] = v
            S.append(int.from_bytes(bytes(s), "little"))
        S.reverse()  # S = (S_{k-1}, ..., S_0)
        rho = 0x01010101
        self.K = []
        for i in range(20):
            A = _h((2 * i * rho) & M32, Me)
            B = _rol(_h(((2 * i + 1) * rho) & M32, Mo), 8)
            self.K.append((A + B) & M32)
            self.K.append(_rol((A + 2 * B) & M32, 9))
        # tablas g() precalculadas: g(X) = T0[b0] ^ T1[b1] ^ T2[b2] ^ T3[b3]
        self.T = [[_mds_col(i, _h_byte(i, x, S)) for x in range(256)] for i in range(4)]

    def _g(self, X):
        T = self.T
        return T[0][X & 0xFF] ^ T[1][(X >> 8) & 0xFF] ^ T[2][(X >> 16) & 0xFF] ^ T[3][X >> 24]

    def encrypt(self, block):
        if len(block) != 16:
            raise ValueError("invalid block length")
        K, g = self.K, self._g
        R = [int.from_bytes(block[4 * i:4 * i + 4], "little") ^ K[i] for i in range(4)]
        r0, r1, r2, r3 = R
        for rnd in range(16):
            t0 = g(r0)
            t1 = g(_rol(r1, 8))
            f0 = (t0 + t1 + K[2 * rnd + 8]) & M32
            f1 = (t0 + 2 * t1 + K[2 * rnd + 9]) & M32
            r2 = _ror(r2 ^ f0, 1)
            r3 = _rol(r3, 1) ^ f1
            r0, r1, r2, r3 = r2, r3, r0, r1
        out = (r2 ^ K[4], r3 ^ K[5], r0 ^ K[6], r1 ^ K[7])
        return b"".join(w.to_bytes(4, "little") for w in out)

    def decrypt(self, block):
        if len(block) != 16:
            raise ValueError("invalid block length")
        K, g = self.K, self._g
        C = [int.from_bytes(block[4 * i:4 * i + 4], "little") for i in range(4)]
        r2, r3, r0, r1 = C[0] ^ K[4], C[1] ^ K[5], C[2] ^ K[6], C[3] ^ K[7]
        for rnd in range(15, -1, -1):
            r0, r1, r2, r3 = r2, r3, r0, r1
            t0 = g(r0)
            t1 = g(_rol(r1, 8))
            f0 = (t0 + t1 + K[2 * rnd + 8]) & M32
            f1 = (t0 + 2 * t1 + K[2 * rnd + 9]) & M32
            r2 = _rol(r2, 1) ^ f0
            r3 = _ror(r3 ^ f1, 1)
        P = (r0 ^ K[0], r1 ^ K[1], r2 ^ K[2], r3 ^ K[3])
        return b"".join(w.to_bytes(4, "little") for w in P)
