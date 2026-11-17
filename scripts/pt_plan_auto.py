#!/usr/bin/env python3
"""Rellena lo MECÁNICO del diseño del alumno y escribe el plan.json que usa pt_apply_plan.py.

Uso: python pt_plan_auto.py red.xml diseno.json plan.json

El alumno decide (esto NO se toca): las redes y su prefijo, los gateways, las IPs de switches y APs,
los rangos de IPs de los hosts, qué clientes van a cada AP y qué red lleva cada etiqueta.

Este script calcula solo lo que es aritmética o está escrito en el lienzo:
  1. la IP exacta de cada host dentro del rango que dio el alumno (de menor a mayor, sin pisar
     gateway, switches ni APs y sin repetir ninguna IP de ningún dispositivo);
  2. las IPs de las interfaces serie a partir de la red /30 o /31 que ya está etiquetada en el lienzo;
  3. las rutas estáticas de cada router (camino más corto por los enlaces entre routers);
  4. el SSID y la clave WPA2 de los APs que el alumno no haya escrito;
  5. junto a qué dispositivos va cada etiqueta de red nueva (router + switch del grupo).

Si el propio diseño del alumno repite una IP, se detiene: eso no se puede aplicar y no se cambia.

Formato del diseño: ../examples/plan_formato.json (sección "grupos"). Las claves de un plan ya
completo (routers, switches, hosts...) se respetan tal cual: aquí solo se rellena lo que falte.
"""
import ipaddress, json, random, string, sys
from collections import deque

try:
    from lxml import etree as ET
    PARSER = ET.XMLParser(strip_cdata=False, huge_tree=True)
except ImportError:  # pragma: no cover
    import xml.etree.ElementTree as ET
    PARSER = None

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

if len(sys.argv) != 4:
    sys.exit(__doc__)
src, draft_path, dst = sys.argv[1:4]

diseno = json.load(open(draft_path, encoding="utf-8"))
plan = json.loads(json.dumps(diseno))  # copia

VARS = {k: str(v).strip() for k, v in diseno.get("variables", {}).items()}


def fail(msg):
    sys.exit("ERROR: " + msg)


def net(s):
    return ipaddress.ip_network(str(s), strict=False)


def usable(n):
    """Direcciones asignables de una red (sin red ni broadcast)."""
    if n.prefixlen >= 31:
        return [n.network_address, n.broadcast_address]
    return [n.network_address + i for i in range(1, n.num_addresses - 1)]


# ---------------- topología del .pka
tree = ET.parse(src, PARSER) if PARSER else ET.parse(src)
r = tree.getroot()
devs, pos = {}, {}
for d in r.find("NETWORK/DEVICES").findall("DEVICE"):
    e = d.find("ENGINE")
    w = d.find("WORKSPACE/LOGICAL")
    devs[e.findtext("NAME")] = e
    try:
        pos[e.findtext("NAME")] = (float(w.findtext("X")), float(w.findtext("Y")))
    except Exception:
        pos[e.findtext("NAME")] = (0.0, 0.0)


def need(name):
    if name not in devs:
        fail(f"el dispositivo '{name}' no existe en el .pka. Hay: {sorted(devs)}")
    return devs[name]


links = []
for l in r.find("NETWORK/LINKS").findall("LINK"):
    c = l.find("CABLE")
    ports = [p.text for p in c.findall("PORT")]
    links.append({
        "type": l.findtext("TYPE") or "",
        "from": c.findtext("FROM"), "fport": ports[0] if ports else None,
        "to": c.findtext("TO"), "tport": ports[1] if len(ports) > 1 else None,
    })
ref2name = {e.findtext("SAVE_REF_ID"): n for n, e in devs.items()}


def ldev(x):
    return ref2name.get(x)


NOTES = [n for n in r.iter("NOTE")]


def note_text(n):
    t = n.findtext("TEXT") or ""
    for k, v in VARS.items():
        t = t.replace(k, v) if k else t
    return t


def is_net_text(t):
    try:
        return net(t.strip())
    except ValueError:
        return False


# ---------------- secciones del plan que se van a rellenar
R = plan.setdefault("routers", {})
S = plan.setdefault("switches", {})
H = plan.setdefault("hosts", {})
APS = plan.setdefault("access_points", {})
WC = plan.setdefault("wireless_clients", {})
SWAP = plan.setdefault("swap_to_wireless", [])
LABELS = plan.setdefault("net_labels", [])

log = []
AVISOS = []            # cosas del diseño que no se corrigen, solo se avisan
USED = {}              # IP -> dispositivo que la tiene. Ninguna IP puede repetirse.
router_nets = {}       # router -> set de redes conectadas
redes = []             # (grupo, red) para detectar solapes entre grupos


def reservar(ip, quien):
    """Anota la IP como usada. Si ya la tenía otro dispositivo, el diseño no se puede aplicar."""
    ip = ipaddress.ip_address(str(ip).split("/")[0])
    if ip in USED:
        fail(f"la IP {ip} está repetida: ya la usa {USED[ip]} y también {quien}. "
             f"Ningún dispositivo puede llevar una IP que ya tiene otro.")
    USED[ip] = quien
    return ip
grupos = diseno.get("grupos", {})

if not grupos:
    log.append("El diseño no trae 'grupos': no hay nada mecánico que calcular.")

for gname, g in grupos.items():
    if "red" not in g or "gateway" not in g:
        fail(f"{gname}: faltan 'red' y/o 'gateway' (eso lo decide el alumno)")
    red = net(g["red"])
    pref = red.prefixlen
    gw = ipaddress.ip_address(str(g["gateway"]))

    # --- avisos del diseño (no se corrige nada: lo decide el alumno)
    red_txt = str(g["red"]).strip()
    if str(red) != red_txt:
        AVISOS.append(f"{gname}: '{red_txt}' no es una dirección de red; se interpreta como {red}.")
    if gw not in red:
        AVISOS.append(f"{gname}: el gateway {gw} no pertenece a la red {red}.")
    for otro, ored in redes:
        if red.overlaps(ored):
            AVISOS.append(f"{gname} ({red}) se solapa con {otro} ({ored}).")
    redes.append((gname, red))

    # --- router del grupo
    rname, rif = g.get("router"), g.get("interfaz")
    if rname and rif:
        need(rname)
        R.setdefault(rname, {}).setdefault("interfaces", {})[rif] = f"{gw}/{pref}"
        reservar(gw, f"{rname} {rif}")
        # red realmente conectada = la de la IP configurada (no se corrige nada: es la del alumno)
        router_nets.setdefault(rname, set()).add(ipaddress.ip_interface(f"{gw}/{pref}").network)
    elif rname:
        fail(f"{gname}: falta 'interfaz' del router {rname}")

    # --- switches (VLAN1 + gateway)
    sw_names = []
    for sname, sip in (g.get("switches") or {}).items():
        need(sname)
        S.setdefault(sname, {}).update({"ip": f"{sip}/{pref}", "gateway": str(gw)})
        reservar(sip, f"{sname} VLAN1")
        sw_names.append(sname)

    # --- APs del grupo
    apname = g.get("ap")
    if apname:
        need(apname)
        ap = APS.setdefault(apname, {})
        clientes = ap.get("clientes") or g.get("clientes_wifi") or []
        ap["clientes"] = clientes
        for cli in clientes:
            need(cli)
            WC[cli] = apname
            e = devs[cli]
            cable = any(
                m.findtext("TYPE") in ("ePtLaptopModule", "ePtHostModule")
                and any(p.findtext("TYPE") == "eCopperFastEthernet" for p in m.findall("PORT"))
                for m in e.iter("MODULE"))
            if cable and cli not in SWAP:
                SWAP.append(cli)

    # --- hosts: IP dentro del rango que dio el alumno
    hnames = g.get("hosts") or []
    rango = g.get("rango")
    given = [H.get(n, {}).get("ip") for n in hnames]
    for n, ip in zip(hnames, given):
        if ip:
            reservar(ip, n)
    if rango in (None, "", "libres") or (isinstance(rango, str) and rango.lower() in ("libres", "auto")):
        cand = [a for a in usable(red) if a not in USED]
    else:
        if not isinstance(rango, (list, tuple)) or len(rango) != 2:
            fail(f"{gname}: 'rango' tiene que ser [inicio, fin] o \"libres\"")

        def extremo(x):
            s = str(x).strip()
            if s.startswith("."):
                return int(red.network_address) + int(s[1:])
            return int(ipaddress.ip_address(s))

        a, b = sorted((extremo(rango[0]), extremo(rango[1])))
        lim = set(usable(red))
        cand = [ipaddress.ip_address(x) for x in range(a, b + 1)
                if ipaddress.ip_address(x) in lim and ipaddress.ip_address(x) not in USED]
    # los que ya traen IP escrita se respetan y liberan del rango
    for n, ip in zip(hnames, given):
        if ip:
            cand = [c for c in cand if c != ipaddress.ip_address(str(ip).split("/")[0])]
    falta = [n for n, ip in zip(hnames, given) if not ip]
    if len(cand) < len(falta):
        fail(f"{gname}: el rango {rango} no tiene {len(falta)} IPs libres para {falta}")
    for n, ip in zip(falta, cand):
        H[n] = {"ip": f"{ip}/{pref}", "gateway": str(gw)}
        reservar(ip, n)
    for n in hnames:
        H.setdefault(n, {})
        H[n].setdefault("gateway", str(gw))
    log.append(f"{gname} ({red}): " + ", ".join(f"{n}={H[n]['ip']}" for n in hnames))

    # --- etiqueta de red del grupo (texto y sitio)
    texto = g.get("etiqueta")
    if texto:
        ya = [note_text(n) for n in NOTES]
        if not any(is_net_text(t) and net(t) == red for t in ya):
            cerca = [x for x in (rname, sw_names[0] if sw_names else (apname or None)) if x]
            if cerca:
                LABELS.append({"text": str(texto), "near": cerca})
                log.append(f"etiqueta {texto} junto a {'/'.join(cerca)}")

# ---------------- WAN: IPs de los enlaces serie a partir de la etiqueta /30 o /31
wan_redes = {str(w.get("routers", "")): net(w["red"]) for w in diseno.get("wan", []) if w.get("red")}
serial = [l for l in links if l["type"] == "eSerial" and ldev(l["from"]) and ldev(l["to"])]
edges = {}
for l in serial:
    a, b = ldev(l["from"]), ldev(l["to"])
    pa, pb = l["fport"], l["tport"]
    key = f"{a}-{b}"
    rn = wan_redes.get(key) or wan_redes.get(f"{b}-{a}")
    if rn is None:
        mx = (pos[a][0] + pos[b][0]) / 2
        my = (pos[a][1] + pos[b][1]) / 2
        best = None
        for n in NOTES:
            t = note_text(n).strip()
            try:
                cand = net(t)
            except ValueError:
                continue
            if cand.prefixlen < 30:
                continue
            d = ((float(n.findtext("X")) - mx) ** 2 + (float(n.findtext("Y")) - my) ** 2) ** 0.5
            if best is None or d < best[0]:
                best = (d, cand)
        if best is None or best[0] > 450:
            fail(f"no encuentro la red /30 del enlace {a} {pa} <-> {b} {pb}: "
                 f"etiquétala en el lienzo o pásala en 'wan'")
        rn = best[1]
    ips = usable(rn)
    if len(ips) < 2:
        fail(f"la red {rn} del enlace {a}-{b} no tiene dos direcciones")
    first, second = sorted([a, b])
    asig = {first: ips[0], second: ips[1]}
    R.setdefault(a, {}).setdefault("interfaces", {})[pa] = f"{asig[a]}/{rn.prefixlen}"
    R.setdefault(b, {}).setdefault("interfaces", {})[pb] = f"{asig[b]}/{rn.prefixlen}"
    reservar(asig[a], f"{a} {pa}")
    reservar(asig[b], f"{b} {pb}")
    router_nets.setdefault(a, set()).add(ipaddress.ip_interface(f"{asig[a]}/{rn.prefixlen}").network)
    router_nets.setdefault(b, set()).add(ipaddress.ip_interface(f"{asig[b]}/{rn.prefixlen}").network)
    edges.setdefault(a, []).append((b, rn, asig[a], asig[b]))
    edges.setdefault(b, []).append((a, rn, asig[b], asig[a]))
    log.append(f"WAN {a} {pa} = {asig[a]}/{rn.prefixlen}  <->  {b} {pb} = {asig[b]}/{rn.prefixlen}")

# ---------------- rutas estáticas: camino más corto entre routers
destinos = sorted({n for ns in router_nets.values() for n in ns}, key=lambda n: (int(n.network_address), n.prefixlen))
for rname in sorted(router_nets):
    propias = router_nets.get(rname, set())
    rutas = R.setdefault(rname, {}).setdefault("routes", [])
    ya = {str(x[0]) for x in rutas}
    for destino in destinos:
        if destino in propias or str(destino) in ya:
            continue
        # BFS: primer salto hacia un router que tenga dst conectada
        q = deque([(rname, None)])
        seen = {rname}
        hop = None
        while q and hop is None:
            cur, first = q.popleft()
            for (peer, _, _, peer_ip) in edges.get(cur, []):
                if peer in seen:
                    continue
                seen.add(peer)
                f = first or (peer, peer_ip)
                if destino in router_nets.get(peer, set()):
                    hop = f
                    break
                q.append((peer, f))
        if hop:
            rutas.append([str(destino), str(hop[1])])
    if rutas:
        log.append(f"rutas {rname}: " + ", ".join(f"{d} via {g}" for d, g in rutas))

# ---------------- aviso: dos interfaces del mismo router en la misma subred
for rname, data in R.items():
    vistas = {}
    for iface, ip in (data.get("interfaces") or {}).items():
        n = ipaddress.ip_interface(ip).network
        if n in vistas:
            AVISOS.append(f"{rname}: {iface} y {vistas[n]} están en la misma red {n}.")
        else:
            vistas[n] = iface

# ---------------- Wi-Fi: SSID y clave si el alumno no los dio
for i, (apname, ap) in enumerate(APS.items(), 1):
    ssid = (ap.get("ssid") or "").strip()
    key = (ap.get("key") or "").strip()
    if not ssid:
        ssid = f"LAB-AP{i}"
    if not key:
        alpha = string.ascii_letters + string.digits
        while True:
            key = "".join(random.SystemRandom().choice(alpha) for _ in range(12))
            if (any(c.islower() for c in key) and any(c.isupper() for c in key)
                    and any(c.isdigit() for c in key)):
                break
    ap["ssid"], ap["key"] = ssid, key
    for cli in ap.get("clientes", []):
        WC[cli] = apname
    log.append(f"AP {apname}: SSID {ssid}  clave {key}  clientes {ap.get('clientes', [])}")

json.dump(plan, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
if AVISOS:
    print("AVISOS DEL DISEÑO (no se corrige nada):")
    for a in AVISOS:
        print("  - " + a)
print("\n".join(log))
print(f"OK -> {dst}")
print("Revisa el plan y ejecuta pt_apply_plan.py. Si algo del diseño es incorrecto, NO se corrige: "
      "se aplica igual y lo descubre la verificación.")
