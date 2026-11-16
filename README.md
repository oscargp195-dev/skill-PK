# packet-tracer-lab: skill para prácticas de Cisco Packet Tracer

Una skill para agentes (Claude Code y compatibles) que **ejecuta el diseño del alumno** en una práctica
de Packet Tracer (`.pka` / `.pkt`) y lo comprueba con pings reales.

**Filosofía:** el agente no diseña, no corrige y no da pistas. El alumno hace el subnetting y decide
las IPs, el enrutamiento (estático, RIP, OSPF o EIGRP), el Wi-Fi y las etiquetas. El agente lo aplica
tal cual y, si algo falla, responde solo:

> **Has fallado en X porque Y. Busca cómo solucionarlo por ti mismo, si lo hago yo NADIE te querrá contratar a TI.**

## Qué hace
- Descifra y vuelve a cifrar `.pka` y `.pkt` de Packet Tracer 7 o superior sin tener PT abierto. Usa
  Twofish-EAX en Python puro, así que en Windows no hay que compilar nada.
- Configura:
  - las IPs de las interfaces de router, las rutas estáticas y RIP, OSPF o EIGRP;
  - la VLAN1 y el default-gateway de los switches;
  - la IP y el gateway de los hosts;
  - WPA2-PSK en los APs y en sus clientes, cambiando las tarjetas de cable por inalámbricas cuando
    hace falta;
  - las etiquetas de red.
- Verifica con pings en Packet Tracer a través del MCP
  [packet-tracer-mcp](https://github.com/Mats2208/MCP-Packet-Tracer) y explica dónde y por qué muere
  cada ping que falla.
- No toca la red de respuesta del `.pka` ni la puntuación de la actividad.

## Instalación (Windows)
1. Copia esta carpeta en `%USERPROFILE%\.claude\skills\packet-tracer-lab`. Otra opción es
   `git clone https://github.com/oscargp195-dev/skill-PK.git "%USERPROFILE%\.claude\skills\packet-tracer-lab"`.
2. La primera vez que se usa, el agente ejecuta `scripts/check_setup.py`. Si falta algo, **pide
   permiso** y ejecuta `scripts/setup_windows.ps1`, que instala:
   - Python 3.12 y uv (con winget);
   - lxml (opcional);
   - el MCP `packet-tracer` en Claude Code;
   - la skill del MCP;
   - la extensión `MCP-Control-Center.pts` de Packet Tracer.
3. Pasos manuales:
   - instalar **Cisco Packet Tracer** (necesita cuenta de NetAcad);
   - reiniciar Claude Code;
   - en PT, aceptar el módulo de script nuevo y abrir **Extensions → MCP BUILDER**.

En Linux o macOS funciona igual con `python3`. Para el MCP:
`claude mcp add --scope user packet-tracer -- uvx packet-tracer-mcp --stdio`.

## Estructura
```
SKILL.md                      instrucciones del agente (reglas y flujo)
examples/plantilla_alumno.json  plantilla vacía del diseño (MN y NC sin rellenar)
examples/plan_formato.json      formato de todos los campos (valores inventados)
reference/xml-format.md       formato XML de PT y trampas conocidas
scripts/ptcrypt.py            .pka/.pkt <-> XML
scripts/pka_split.py          separa y une la red del alumno
scripts/pt_summary.py         resumen de la topología y el enunciado
scripts/pt_apply_plan.py      aplica el diseño del alumno
scripts/check_setup.py        comprueba las dependencias
scripts/setup_windows.ps1     instala las dependencias (con permiso)
scripts/lib/                  Twofish: Python puro y extensión C opcional (Linux)
```

`scripts/lib/twofish.py` y `_twofish*.so` vienen de *Python Twofish* (Keybase, licencia BSD-3).
`twofish_py.py` es una implementación propia en Python puro, comprobada con el vector de prueba
oficial y contra la extensión C.
