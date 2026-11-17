---
name: packet-tracer-lab
description: >-
  Monta, configura, comprueba y corrige prácticas de Cisco Packet Tracer (.pka / .pkt). Lee la topología,
  agrupa los dispositivos por LAN, hace el subnetting, asigna IPs, gateways, rutas (estático, RIP, OSPF,
  EIGRP), SSID y claves Wi-Fi WPA2, pone etiquetas de red, lo aplica en el .pka, lo prueba con pings en
  Packet Tracer vía MCP y explica y arregla lo que falle. Úsala cuando pidan "configura/monta mi práctica
  de Packet Tracer", "aplica mi direccionamiento", "comprueba/arregla mi diseño" o pasen un .pka/.pkt.
  La primera vez instala (con permiso) Python, uv, el MCP packet-tracer y la extensión de PT en Windows.
---

# Packet Tracer Lab

Haces todo el trabajo de la práctica: diseño (subnetting, IPs, gateways, rutas, Wi-Fi, etiquetas),
aplicación en el archivo, verificación con pings y corrección de fallos. Si el usuario da su propio
diseño, úsalo; si falta algo, complétalo tú. Puedes explicar, dar pistas, dar la solución y usar
cualquier herramienta del MCP (`pt_plan_topology`, `pt_full_build`, `pt_fix_plan`, `pt_health_check`,
`pt_live_deploy`, `pt_activity_*`…) y cualquier bloque del `.pka`.

`SK` = carpeta de esta skill. En Windows usa `python`; en Linux o macOS, `python3`. Trabaja siempre en
una carpeta temporal y **no sobrescribas el archivo original**.

## 0. Primera vez en este equipo: instalación (pide permiso)

```
python SK/scripts/check_setup.py
```
Si todo sale `OK`, pasa al paso 1. Si falta algo, **enseña al alumno la lista de lo que falta y pide
permiso** con AskUserQuestion: "Voy a instalar: … ¿Continúo?". Si acepta, en Windows ejecuta:
```
powershell -ExecutionPolicy Bypass -File "SK\scripts\setup_windows.ps1"
```
Ese script hace lo siguiente (cada paso solo si hace falta):
- Instala Python 3.12 y uv con winget.
- Instala lxml con pip (es opcional).
- Registra el MCP con `claude mcp add --scope user packet-tracer -- uvx packet-tracer-mcp --stdio`.
- Instala la skill del MCP con `uvx packet-tracer-mcp install-skill`.
- Descarga la extensión `MCP-Control-Center.pts` y la copia en la carpeta `extensions` de Packet
  Tracer. Solo puede copiarla si tiene permisos de administrador; si no, explica cómo añadirla desde PT.

Después vuelve a lanzar `check_setup.py`. Hay tres cosas que el alumno tiene que hacer a mano:
- Instalar **Cisco Packet Tracer** (necesita su cuenta de NetAcad).
- **Reiniciar Claude Code** para que cargue el MCP.
- En PT, aceptar el módulo nuevo y abrir **Extensions → MCP BUILDER**.

Si no hay MCP, la skill funciona igual (todo se hace editando el archivo), pero los pings los tendrá
que hacer el alumno.

## 1. Leer la práctica
```
python SK/scripts/ptcrypt.py d Lab.pka full.xml
python SK/scripts/pka_split.py split full.xml red.xml      # 1er bloque (red del alumno); el 2º y 3º son la respuesta y la inicial
python SK/scripts/pt_summary.py red.xml full.xml           # dispositivos, puertos, enlaces, notas, enunciado
```
`full.xml` no es XML válido (lleva bytes binarios), así que no lo abras entero con un parser.
Enseña un resumen de la topología: dispositivos, interfaces conectadas y a qué, notas del lienzo y
el texto del enunciado. Puedes añadir cuántas subredes hacen falta, su tamaño y cualquier consejo.

## 2. Leer el diseño (de un archivo, o hazlo tú)
Si el usuario entrega su diseño en un archivo (`SK/examples/plantilla_alumno.json` rellenada, un
`plan.json` o un texto), léelo. Si falta algún dato, **complétalo tú** (subnetting, IPs, gateways,
rutas, SSID, claves, etiquetas) y, si hace falta, pregunta. Si no hay diseño, hazlo entero tú.

| Dato | Ejemplo de forma (no de valor) |
|---|---|
| **Variables del enunciado** (`MN`, `NC`…) | `"MN": "6"` |
| **Grupos**: una LAN por cada interfaz de router. Red con prefijo, gateway y a qué router/interfaz va | `"G1": {"red": "a.b.c.d/nn", "gateway": "…", "router": "Router0", "interfaz": "GigabitEthernet0/0/0"}` |
| **Switches**: IP de cada uno (VLAN1), dentro de su grupo | `"switches": {"Switch1": "…"}` |
| **Hosts**: qué equipos van en cada grupo y **el rango de IPs** que les asigna | `"hosts": ["PC0","PC1"], "rango": [".2",".6"]` o `"rango": "libres"` |
| **Wi-Fi**: qué clientes van a cada AP | `"ap": "Access Point0", "clientes_wifi": ["PC6","PC7"]` |
| **Etiquetas de red**: texto o red de cada etiqueta nueva | `"etiqueta": "a.b.c.d/nn"` |
| Hostnames (opcional) y SSID/clave si los quiere fijar él | |

- Si el enunciado tiene variables como `MN` o `NC`, pregunta su valor o dedúcelo.
- Pasar los datos al formato JSON es trabajo tuyo. El formato completo está en
  `SK/examples/plan_formato.json`.

## 3. Rellenar lo que falte
```
python SK/scripts/pt_plan_auto.py red.xml diseno.json plan.json
```
Lee el diseño y la red del `.pka`, y escribe el `plan.json` que se aplica después. Rellena, con reglas
fijas:
- **IP de cada host**: recorre el rango que dio él de menor a mayor, salta las que ya usan gateway,
  switches y APs, y asigna en el orden en que él lista los equipos del grupo.
- **IPs de los enlaces serie**: toma la red `/30` o `/31` de la etiqueta que ya está en el lienzo; el
  router cuyo nombre va primero se queda la dirección baja (`.1`) y el otro la siguiente.
- **Rutas estáticas**: camino más corto por los enlaces entre routers, con red destino y siguiente salto.
- **Wi-Fi**: si no dio SSID, `LAB-AP<n>`; si no dio clave, 12 caracteres al azar con mayúscula,
  minúscula y dígito (WPA2-PSK). Pasa a inalámbricos los equipos que estén a cable.
- **Etiquetas**: coloca cada una junto al router y el switch principal de su grupo.
- **Ninguna IP se repite**: lleva una lista global con todas las IPs (gateways, switches, hosts y
  enlaces) y no asigna ninguna dos veces. Si es el diseño del alumno el que repite una IP, se detiene
  y dice qué dos dispositivos la comparten; no la cambia. `pt_apply_plan.py` vuelve a comprobarlo
  antes de escribir nada.

Comprueba el resumen que imprime y corrige lo que esté mal (solapes de redes, gateways fuera de su
red, etc.) antes de aplicar.

## 4. Aplicar y empaquetar
```
python SK/scripts/pt_apply_plan.py red.xml plan.json red_new.xml
python SK/scripts/pka_split.py merge full.xml red_new.xml full_new.xml
python SK/scripts/ptcrypt.py e full_new.xml Lab_configurado.pka
python SK/scripts/ptcrypt.py d Lab_configurado.pka check.xml        # comprobación de ida y vuelta
python SK/scripts/pka_split.py split check.xml chk.xml
python SK/scripts/pt_summary.py chk.xml
```
- `pt_apply_plan.py` aplica lo que pone el plan. Se detiene si el plan no se puede aplicar: un
  dispositivo o una interfaz que no existe, una IP mal escrita o una variable vacía. Dile qué pasa y
  arréglalo.
- Compara el resumen final con el diseño para asegurarte de que se ha copiado bien.
- Guarda `<nombre>_configurado.pka` junto al original y comprueba el tamaño con `ls` o `dir`.

## 5. Verificar con pings (MCP packet-tracer)
1. Ejecuta `pt_bridge_status`. Si PT no está conectado, pide que abran PT y
   **Extensions → MCP BUILDER**.
2. `pt_open_project` **solo acepta `.pkt`**. Copia el `.pka` configurado a la carpeta temporal con
   extensión `.pkt` y ábrelo. Después ejecuta `pt_query_topology` y `pt_fast_forward`.
3. **Lanza los pings** con `pt_verify_connectivity`:
   - un host de cada LAN contra un host de cada una de las otras LAN;
   - cada host contra su gateway;
   - un host contra la IP de cada switch;
   - un host contra cada interfaz serie;
   - todos los clientes Wi-Fi.

   Si un ping falla o pierde paquetes, **repítelo una vez**: el primero puede perderse por ARP o
   porque el Wi-Fi todavía se está asociando. Con 100 % de pérdida en el segundo intento, cuenta
   como fallo. Si pierde algunos paquetes pero llega alguno, cuenta como OK.
4. Para cada fallo, averigua el motivo con `pt_send_pdu(source, destination, steps=10)`,
   `pt_read_device_panel`, `pt_read_routes`, `pt_inspect_ports`, etc., y **arréglalo** (en el
   archivo o en PT), explicando qué estaba mal y cómo lo has solucionado. Vuelve a probar.
5. No digas que algo funciona si no has visto el ping responder.

## 6. Informe (en español)
- **Lo que se ha aplicado**: una tabla con sus propios datos (red, interfaces, rutas o protocolo,
  switches, hosts, SSID) y la ruta del `.pka` configurado.
- **Pings OK**: la lista.
- **Fallos**: uno por línea, con el motivo y cómo se ha solucionado (o cómo solucionarlo).
- Si no hay MCP, dale la lista exacta de pings para que los haga él (PC → Desktop → Command Prompt).

Si el usuario manda un diseño corregido, vuelve a aplicarlo **desde el archivo original** (paso 4)
y verifica otra vez (paso 5).

## Trampas técnicas conocidas (lo mecánico sí lo resuelves tú)
- Solo se edita el 1er `<PACKETTRACER5>`; el resto del archivo se copia byte a byte (`pka_split`).
- PT aplica la `RUNNINGCONFIG` al abrir. El script quita ` shutdown` en las interfaces que usa el plan.
- Hosts con IP estática: el script vacía `DHCP_CLIENT/PORT_DATA_MAP` y pone la IP en **todos** los
  perfiles Wi-Fi (`CURRENT_PROFILE` y `PROFILES`). Si no, PT pide DHCP al abrir y el host acaba con
  169.254.x.x (pasó con PC7 del Lab07). Si aun así un host sale con 169.254.x.x o 0.0.0.0, el problema
  es del script: revísalo.
- Cambiar la tarjeta de cable por una inalámbrica (`swap_to_wireless`) por XML es lo más frágil. Si un
  cliente no se asocia y su SSID y clave coinciden con las del AP, pide al alumno que cambie la tarjeta
  a mano (pestaña Physical, WPC300N o WMP300N).
- El MCP no puede configurar WPA en los clientes (solo desde la interfaz gráfica); por XML sí. No
  configures el Wi-Fi por MCP.
- `pt_plan_auto.py` no valida el diseño: revisa tú solapes de redes y gateways antes de aplicar.
- El `.pka` no guarda IP en los APs (`AccessPoint-PT`): si el alumno asigna IP a un AP, no hay dónde
  ponerla. De un AP solo se configuran SSID y clave.
- Cifrado: `ptcrypt.py` usa la extensión C de Twofish si la hay (Linux) y, si no, `lib/twofish_py.py`
  en Python puro (Windows; tarda unos 3 s por archivo).
- Detalle del formato XML: [reference/xml-format.md](reference/xml-format.md).
