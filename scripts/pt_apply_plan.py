#!/usr/bin/env python3
"""Aplica el DISEÑO DEL ALUMNO (plan JSON) a una red de Packet Tracer: IPs, rutas estáticas,
RIP/OSPF/EIGRP, switches, Wi-Fi WPA2 y etiquetas de red.

Uso: python pt_apply_plan.py red.xml plan.json red_editada.xml
Formato del plan: ../examples/plan_formato.json (plantilla vacía: ../examples/plantilla_alumno.json).
Prefijos en notación CIDR ("172.22.0.1/18").

Este script NO valida ni corrige el diseño: aplica exactamente lo que dice el plan. Solo se detiene
si el plan no se puede aplicar (dispositivo o interfaz inexistente, variable sin rellenar...).
"""
import ipaddress, json, random, sys, uuid

try:
    from lxml import etree as ET  # conserva CDATA
    PARSER = ET.XMLParser(strip_cdata=False, huge_tree=True)
    LXML = True
except ImportError:  # pragma: no cover
    import xml.etree.ElementTree as ET
    PARSER = None
    LXML = False

try:
    sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows (cp1252)
except Exception:
    pass

if len(sys.argv) != 4:
    sys.exit(__doc__)
src, plan_path, dst = sys.argv[1:4]
plan = json.load(open(plan_path, encoding="utf-8"))

# variables del enunciado (MN, NC...): las rellena el ALUMNO; vacías = no se puede seguir
VARS = {k: str(v).strip() for k, v in plan.get("variables", {}).items()}
_empty = [k for k, v in VARS.items() if v == ""]
if _empty:
    sys.exit(f"ERROR: variables sin rellenar en el plan: {_empty}. Las tiene que dar el alumno.")
tree = ET.parse(src, PARSER) if LXML else ET.parse(src)
r = tree.getroot()
devs = {d.find("ENGINE").findtext("NAME"): d for d in r.find("NETWORK/DEVICES").findall("DEVICE")}
log = []


def need(name):
    if name not in devs:
        sys.exit(f"ERROR: el dispositivo '{name}' no existe. Disponibles: {sorted(devs)}")
    return devs[name].find("ENGINE")


def sub(p, tag, val):
    el = p.find(tag)
    if el is None:
        el = ET.SubElement(p, tag)
    el.text = val
    return el


def cidr(s):
    i = ipaddress.ip_interface(s)
    return str(i.ip), str(i.network.netmask)


def net(s):
    n = ipaddress.ip_network(s, strict=False)
    return str(n.network_address), str(n.netmask)


def cfg_lines(e):
    return [l.text or "" for l in e.find("RUNNINGCONFIG")]


def set_cfg(e, lines):
    # running-config y startup-config iguales (equivale a "write memory")
    for tag in ("RUNNINGCONFIG", "STARTUPCONFIG"):
        c = e.find(tag)
        for ch in list(c):
            c.remove(ch)
        for l in lines:
            ET.SubElement(c, "LINE").text = l


def _netwc(n):
    """'172.22.0.0/18' -> ('172.22.0.0', '0.0.63.255'); ['172.22.0.0', '0.0.63.255'] se deja tal cual."""
    if isinstance(n, (list, tuple)):
        return n[0], n[1]
    x = ipaddress.ip_network(n, strict=False)
    return str(x.network_address), str(x.hostmask)


def routing_lines(c):
    """Bloques 'router ...' tal y como los ha diseñado el alumno. Se insertan antes de 'ip classless'."""
    out = []
    o = c.get("ospf")
    if o:
        out.append(f"router ospf {o.get('process', 1)}")
        if o.get("router_id"):
            out.append(f" router-id {o['router_id']}")
        for p in o.get("passive", []):
            out.append(f" passive-interface {p}")
        for n in o.get("networks", []):
            if isinstance(n, dict):
                a, w = _netwc(n["net"]); area = n.get("area", 0)
            elif isinstance(n, (list, tuple)) and len(n) == 3:
                a, w, area = n
            else:
                (a, w), area = _netwc(n), o.get("area", 0)
            out.append(f" network {a} {w} area {area}")
        if o.get("default_originate"):
            out.append(" default-information originate")
        out.append("!")
    rp = c.get("rip")
    if rp:
        out.append("router rip")
        if rp.get("version"):
            out.append(f" version {rp['version']}")
        for p in rp.get("passive", []):
            out.append(f" passive-interface {p}")
        for n in rp.get("networks", []):
            out.append(f" network {str(n).split('/')[0]}")
        if rp.get("no_auto_summary"):
            out.append(" no auto-summary")
        if rp.get("default_originate"):
            out.append(" default-information originate")
        out.append("!")
    eg = c.get("eigrp")
    if eg:
        out.append(f"router eigrp {eg.get('as', 1)}")
        if eg.get("router_id"):
            out.append(f" eigrp router-id {eg['router_id']}")
        for p in eg.get("passive", []):
            out.append(f" passive-interface {p}")
        for n in eg.get("networks", []):
            if isinstance(n, str) and "/" not in n:
                out.append(f" network {n}")
            else:
                out.append(" network %s %s" % _netwc(n))
        if eg.get("no_auto_summary"):
            out.append(" no auto-summary")
        out.append("!")
    out += list(c.get("extra_config", []))  # líneas IOS literales que dicte el alumno
    return out


PHYS = ("Ethernet", "Serial")  # tipos de PORT físicos que aparecen como "interface X" en la config

# ---------------- routers
for name, c in plan.get("routers", {}).items():
    e = need(name)
    ifs = {k: cidr(v) for k, v in c.get("interfaces", {}).items()}
    lines, out, cur, order = cfg_lines(e), [], None, []
    for l in lines:
        if l.startswith("hostname ") and c.get("hostname"):
            out.append("hostname " + c["hostname"]); continue
        if l.startswith("interface "):
            cur = l.split()[1]
            order.append(cur)
        elif not l.startswith(" "):
            cur = None
        if cur in ifs:
            if l == " no ip address":
                out.append(" ip address %s %s" % ifs[cur]); continue
            if l == " shutdown":
                continue
        if l == "ip classless":
            out += routing_lines(c)
        out.append(l)
        if l == "ip classless":
            for dest, gw in c.get("routes", []):
                out.append("ip route %s %s %s " % (*net(dest), gw))
    missing = set(ifs) - set(order)
    if missing:
        sys.exit(f"ERROR {name}: interfaces inexistentes {missing}. Existen: {order}")
    if "no ip domain-lookup" not in out and "no ip cef" in out:
        i = out.index("no ip cef"); out[i:i] = ["no ip domain-lookup", "!"]
    set_cfg(e, out)
    if c.get("hostname"):
        sub(e, "SYS_NAME", c["hostname"])
    # PORT del XML en el mismo orden que las interfaces físicas de la config
    phys_if = [i for i in order if any(k in i for k in PHYS)]
    ports = [p for p in e.iter("PORT") if any(k in (p.findtext("TYPE") or "") for k in PHYS)]
    if len(phys_if) == len(ports):
        for ifn, p in zip(phys_if, ports):
            if ifn in ifs:
                sub(p, "IP", ifs[ifn][0]); sub(p, "SUBNET", ifs[ifn][1])
                sub(p, "POWER", "true"); sub(p, "PORT_DHCP_ENABLE", "false")
    else:
        log.append(f"AVISO {name}: {len(phys_if)} interfaces vs {len(ports)} PORT; solo se tocó la config")
    proto = [p for p in ("ospf", "rip", "eigrp") if c.get(p)]
    log.append(f"router {name}: {len(ifs)} interfaces, {len(c.get('routes', []))} rutas estáticas"
               + (f", {'/'.join(proto)}" if proto else ""))

# ---------------- switches (SVI VLAN1 + default-gateway)
for name, c in plan.get("switches", {}).items():
    e = need(name)
    ip, m = cidr(c["ip"])
    out, cur = [], None
    for l in cfg_lines(e):
        if l.startswith("hostname ") and c.get("hostname"):
            out.append("hostname " + c["hostname"]); continue
        if l.startswith("ip default-gateway"):
            continue
        if l.startswith("interface "):
            cur = l.split()[1]
        elif not l.startswith(" "):
            if cur == "Vlan1" and c.get("gateway"):
                out += ["!", "ip default-gateway " + c["gateway"]]
            cur = None
        if cur == "Vlan1":
            if l == " no ip address" or l.startswith(" ip address"):
                out.append(f" ip address {ip} {m}"); continue
            if l == " shutdown":
                continue
        out.append(l)
    set_cfg(e, out)
    if c.get("hostname"):
        sub(e, "SYS_NAME", c["hostname"])
    log.append(f"switch {name}: VLAN1 {ip}")

# ---------------- cambiar tarjeta de red cableada por inalámbrica
WIRELESS_MODEL = {"ePtLaptopModule": "Linksys-WPC300N", "ePtHostModule": "Linksys-WMP300N"}
for name in plan.get("swap_to_wireless", []):
    e = need(name)
    done = False
    for mod in e.iter("MODULE"):
        mt = mod.findtext("TYPE")
        p = mod.find("PORT")
        if mt in WIRELESS_MODEL and p is not None and p.findtext("TYPE") == "eCopperFastEthernet":
            mod.find("MODEL").text = WIRELESS_MODEL[mt]
            p.find("TYPE").text = "eHostWirelessN"
            sub(p, "BANDWIDTH", "54000")
            sub(p, "AUTONEGOTIATEBANDWIDTH", "true"); sub(p, "AUTONEGOTIATEDUPLEX", "true")
            done = True
    log.append(f"tarjeta Wi-Fi {name}: {'OK' if done else 'NO ENCONTRADA (¿ya era inalámbrico o tiene cable?)'}")

# ---------------- hosts (IP estática)
for name, c in plan.get("hosts", {}).items():
    e = need(name)
    ip, m = cidr(c["ip"])
    gw = c.get("gateway", "")
    sub(e, "GATEWAY", gw)
    for p in e.iter("PORT"):
        if p.findtext("TYPE") in ("eCopperFastEthernet", "eHostWirelessN", "eCopperGigabitEthernet"):
            sub(p, "IP", ip); sub(p, "SUBNET", m); sub(p, "PORT_GATEWAY", gw); sub(p, "PORT_DHCP_ENABLE", "false")
    # IP estática: quitar los puertos del cliente DHCP (si no, PT pide DHCP al abrir y pone 0.0.0.0 / 169.254.x.x)
    for dc in e.iter("DHCP_CLIENT"):
        for pdm in dc.findall("PORT_DATA_MAP"):
            for ent in pdm.findall("PORT_DATA_ENTRY"):
                pdm.remove(ent)
    log.append(f"host {name}: {ip}/{m} gw {gw}")


# ---------------- Wi-Fi (WPA2-PSK: AUTHEN_TYPE=4, ENCRYPT_TYPE=4 AES)
def set_common(wc, ssid, key):
    sub(wc, "SSID", ssid); sub(wc, "ENCRYPT_TYPE", "4"); sub(wc, "AUTHEN_TYPE", "4")
    wp = wc.find("WEP_PROCESS")
    if wp is None:
        wp = ET.Element("WEP_PROCESS")
        kids = list(wc)
        idx = kids.index(wc.find("STANDARD_CHANNEL")) + 1 if wc.find("STANDARD_CHANNEL") is not None else len(kids)
        wc.insert(idx, wp)
        for t in ("KEY", "USERID", "PASSWORD", "ENCRYPTION"):
            ET.SubElement(wp, t)
    wp.find("KEY").text = key
    wp.find("ENCRYPTION").text = "4"


aps = plan.get("access_points", {})
for name, c in aps.items():
    e = need(name)
    set_common(e.find("WIRELESS_SERVER/WIRELESS_COMMON"), c["ssid"], c["key"])
    log.append(f"AP {name}: SSID {c['ssid']} WPA2-PSK")
for name, ap in plan.get("wireless_clients", {}).items():
    e = need(name)
    ssid, key = aps[ap]["ssid"], aps[ap]["key"]
    w = e.find("WIRELESS_CLIENT")
    wc = w.find("WIRELESS_COMMON")
    set_common(wc, ssid, key); sub(wc, "NETWORK_MODE", "7")
    cp = w.find("CURRENT_PROFILE/WIRELESS_PROFILE")
    h = plan.get("hosts", {}).get(name)
    vals = [("SSID", ssid), ("NETWORK_TYPE", "3"), ("AUTHEN_TYPE", "4"), ("ENCRYPT_TYPE", "4"), ("WEP_KEY", key)]
    if h:
        ip, m = cidr(h["ip"])
        vals += [("DHCP_ENABLED", "0"), ("IP_ADDRESS", ip), ("SUBNET_MASK", m), ("DEFAULT_GATEWAY", h.get("gateway", ""))]
    # todos los perfiles (actual + guardados en PROFILES): un perfil "Default" con DHCP=1 deja el host en 169.254.x.x
    for prof in w.iter("WIRELESS_PROFILE"):
        for t, v in vals:
            sub(prof, t, v)
    log.append(f"cliente Wi-Fi {name} -> {ssid}")

# ---------------- notas / etiquetas
notes = list(r.iter("NOTE"))
for n in notes:
    t = n.findtext("TEXT")
    if t in plan.get("rename_notes", {}):
        n.find("TEXT").text = t = plan["rename_notes"][t]
    if t and VARS:  # 192.168.NC.0/24 -> 192.168.7.0/24 (solo sustitución literal, sin calcular nada)
        import re as _re
        nt = _re.sub(r"\b(" + "|".join(map(_re.escape, VARS)) + r")\b", lambda m: VARS[m.group(1)], t)
        if nt != t:
            n.find("TEXT").text = nt
            log.append(f"etiqueta '{t}' -> '{nt}'")
parent = r.find("NETWORK/NOTES") if r.find("NETWORK/NOTES") is not None else None
if parent is None:
    parent = next(iter(r.iter("NOTE"))).getparent() if (LXML and notes) else None
if parent is None:
    for el in r.iter():
        if el.tag.endswith("NOTES"):
            parent = el; break
z = [40100]


def note(x, y, text):
    n = ET.SubElement(parent, "NOTE", uuid="{%s}" % uuid.uuid4())
    for t, v in (("X", str(x)), ("Y", str(y)), ("Z", str(z[0]))):
        ET.SubElement(n, t).text = v
    ET.SubElement(n, "TEXT", translate="true").text = text
    ET.SubElement(n, "NOTECLUSTERID").text = "1-1"
    ET.SubElement(n, "MEM_ADDR").text = str(random.randint(10**14, 2 * 10**14))
    z[0] += 2


def pos(name):
    w = devs[name].find("WORKSPACE/LOGICAL")
    return float(w.findtext("X")), float(w.findtext("Y"))


if parent is None:
    log.append("AVISO: no se encontró contenedor de notas; no se añadieron etiquetas")
else:
    for x, y, text in plan.get("notes", []):
        note(x, y, text)
    # etiquetas de red junto a dispositivos: {"text": "172.22.0.0/18", "near": ["Router0", "Switch1"], "dx": 0, "dy": 0}
    # (un dispositivo = al lado; dos = en el punto medio del enlace)
    for lab in plan.get("net_labels", []):
        pts = [pos(d) for d in lab["near"]]
        x = sum(p[0] for p in pts) / len(pts) + lab.get("dx", 0 if len(pts) > 1 else 45)
        y = sum(p[1] for p in pts) / len(pts) + lab.get("dy", 0)
        note(round(x), round(y), lab["text"])
        log.append(f"etiqueta {lab['text']} junto a {'/'.join(lab['near'])}")
    # Etiquetas de dispositivos/interfaces/VLAN1/SSID: DESACTIVADAS por defecto (solo etiquetas de red)
    if plan.get("auto_labels", False):
        for name, c in plan.get("routers", {}).items():
            x, y = pos(name)
            txt = "\n".join(f"{k.replace('GigabitEthernet', 'G').replace('FastEthernet', 'F').replace('Serial', 'S')} {v.split('/')[0]}"
                            for k, v in c.get("interfaces", {}).items())
            dx = c.get("label_dx", -95)
            note(x + dx, y + 5, txt)
        for name, c in plan.get("switches", {}).items():
            x, y = pos(name)
            note(x + c.get("label_dx", 40), y + 28, "VLAN1 " + c["ip"].split("/")[0])
        for name, c in plan.get("hosts", {}).items():
            x, y = pos(name)
            note(x - 12, y + 50, c["ip"].split("/")[0])
        for name, c in aps.items():
            x, y = pos(name)
            note(x + 30, y - 28, f"SSID: {c['ssid']}\nWPA2-PSK")

tree.write(dst, encoding="utf-8")
print("\n".join(log))
print(f"OK -> {dst}")
