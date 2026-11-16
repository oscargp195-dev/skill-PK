#!/usr/bin/env python3
"""Resume una red de Packet Tracer (XML de un bloque PACKETTRACER5, ver pka_split.py).

Muestra: dispositivos (modelo, posición, módulos, IPs, hostname), enlaces (con lado DCE),
notas del lienzo (etiquetas de red) y el texto del enunciado si se pasa el XML completo.

Uso: python3 pt_summary.py red.xml [completo.xml]
"""
import re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows
except Exception:
    pass
import xml.etree.ElementTree as ET

r = ET.parse(sys.argv[1]).getroot()
net = r.find("NETWORK")
ids = {}
print("== DISPOSITIVOS")
for d in net.find("DEVICES").findall("DEVICE"):
    e = d.find("ENGINE")
    name = e.findtext("NAME")
    ids[e.findtext("SAVE_REF_ID")] = name
    t = e.find("TYPE")
    w = d.find("WORKSPACE/LOGICAL")
    xy = (w.findtext("X"), w.findtext("Y")) if w is not None else ("?", "?")
    host = next((l.text[9:] for l in (e.find("RUNNINGCONFIG") if e.find("RUNNINGCONFIG") is not None else []) if (l.text or "").startswith("hostname ")), "")
    print(f"- {name} [{t.text} {t.get('model')}] xy={xy} {('hostname=' + host) if host else ''}")
    for m in e.iter("MODULE"):
        if m.findtext("MODEL"):
            ps = [p.findtext("TYPE") for p in m.findall("PORT")]
            print(f"    módulo {m.findtext('MODEL')}: {ps}")
    for p in e.iter("PORT"):
        if p.findtext("IP"):
            print(f"    IP {p.findtext('TYPE')} {p.findtext('IP')}/{p.findtext('SUBNET')}")
    if e.findtext("GATEWAY"):
        print(f"    gateway {e.findtext('GATEWAY')}")
    for tag in ("WIRELESS_SERVER", "WIRELESS_CLIENT"):
        wc = e.find(tag + "/WIRELESS_COMMON")
        if wc is not None:
            print(f"    {tag}: SSID={wc.findtext('SSID')} auth={wc.findtext('AUTHEN_TYPE')} enc={wc.findtext('ENCRYPT_TYPE')}")
    rc = e.find("RUNNINGCONFIG")
    if rc is not None:
        blk = False
        for l in rc:
            s = l.text or ""
            if s.startswith("router "):
                blk = True
            elif not s.startswith(" "):
                blk = False
            if blk or s.startswith(("ip route", " ip address", "ip default-gateway")):
                print("    cfg:", s.rstrip())
print("== ENLACES")
for l in net.find("LINKS").findall("LINK"):
    c = l.find("CABLE")
    p = c.findall("PORT")
    dce = c.findtext("DCEDEV")
    extra = f"  (DCE: {ids.get(dce)} {c.findtext('DCEPORT')})" if dce else ""
    print(f"- {ids.get(c.findtext('FROM'))} {p[0].text} <-> {ids.get(c.findtext('TO'))} {p[1].text} [{l.findtext('TYPE')}]{extra}")
print("== NOTAS (etiquetas)")
for n in r.iter("NOTE"):
    print(f"- ({n.findtext('X')},{n.findtext('Y')}) {(n.findtext('TEXT') or '').replace(chr(10), ' | ')}")
if len(sys.argv) > 2:
    full = open(sys.argv[2], "rb").read().decode("utf-8", "replace")
    m = re.search(r"<INSTRUCTIONS.*?<PAGE[^>]*><!\[CDATA\[(.*?)\]\]>", full, re.S)
    if m:
        txt = re.sub(r"<[^>]+>", " ", m.group(1)).replace("&nbsp;", " ")
        print("== ENUNCIADO\n" + re.sub(r"\s+", " ", txt).strip())
