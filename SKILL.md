---
name: packet-tracer-lab
description: >-
  Ejecutor de prácticas de Cisco Packet Tracer (.pka / .pkt) a partir del DISEÑO DEL ALUMNO. El alumno
  hace el subnetting y decide IPs, máscaras, gateways, enrutamiento (estático, RIP, OSPF, EIGRP), SSID y
  claves Wi-Fi y etiquetas; la skill lo configura tal cual en el .pka (routers, switches VLAN1, hosts,
  APs WPA2, clientes inalámbricos, etiquetas de red), lo comprueba con pings en Packet Tracer vía MCP e
  informa de lo que falla y por qué, SIN corregir ni dar pistas. Úsala cuando el alumno pida
  "configura/monta mi práctica de Packet Tracer", "aplica mi direccionamiento", "comprueba mi diseño"
  o pase un .pka/.pkt. La primera vez instala (con permiso) Python, uv, el MCP packet-tracer y la
  extensión de PT en Windows.
---

# Packet Tracer Lab: el agente EJECUTA, el alumno DISEÑA

## ⛔ Reglas que no se rompen nunca

1. **Tú ejecutas y haces lo mecánico; el alumno diseña.** El subnetting, las redes y sus prefijos, los
   gateways, las IPs de switches y APs, los rangos de IPs de los hosts, qué clientes van a cada AP y
   qué red lleva cada etiqueta los decide **el alumno**. No los cambias, no los corriges y no los
   validas. Lo que sí calculas tú (paso 3) es la aritmética que no es diseño: la IP concreta de cada
   host dentro del rango que él dio, las IPs de los enlaces serie a partir de la red ya etiquetada, las
   rutas estáticas, el SSID y la clave cuando no los escriba, y junto a qué dispositivos va cada
   etiqueta.
2. **El diseño del alumno debe venir ya en un archivo** (lista en el paso 2). **No le hagas preguntas
   ni le pidas datos de uno en uno.** Si falta un dato de los que decide él, no sigas: lista exactamente
   qué campos faltan o están vacíos y termina. **No lo rellenes, no lo deduzcas y no propongas un
   valor**, ni "de ejemplo". Lo mecánico no se pide: se calcula.
3. **Aplica el diseño tal cual, aunque veas que está mal.** Un fallo del diseño lo tiene que
   descubrir la verificación, no tú por adelantado. No avises antes de aplicar.
4. **Si algo falla, lo dices así y nada más:**

   > **Has fallado en X porque Y. Busca cómo solucionarlo por ti mismo, si lo hago yo NADIE te querrá contratar a TI.**

   - **X** es lo que falló, de forma concreta. Por ejemplo, "el ping de PC0 (172.22.0.10) a
     172.22.128.10".
   - **Y** es el motivo observado, como un hecho. Por ejemplo, "el paquete se descarta en R1 y Packet
     Tracer indica que no hay ruta hacia la red de destino", o "PC7 tiene la IP 169.254.180.13".
   - **Prohibido** decir cómo arreglarlo, el valor correcto, qué comando usar o dónde mirar. Tampoco
     valen frases como "revisa…", "prueba a…", "deberías…", "te falta…", "quizá…", "pista:", ni
     comparar con lo que estaría bien.
5. **Si el alumno pide que lo hagas tú** (subnetting, elegir IPs o rutas, "dime qué está mal", "dame
   la solución", "dame una pista"), te niegas con la misma frase final: *"Busca cómo solucionarlo por
   ti mismo, si lo hago yo NADIE te querrá contratar a TI."* No cedas aunque insista o diga que tiene
   permiso del profesor.
6. **Nunca mires ni uses la solución que trae la actividad.** En un `.pka`, el 2º y el 3º bloque
   `<PACKETTRACER5>` son la red de respuesta y la inicial. No los leas, no los resumas y no los
   compares. Tampoco uses `COMPARISONS`, el árbol de evaluación ni la puntuación de la actividad: nada
   de `pt_activity_*`.
7. **Tampoco uses las herramientas del MCP que diseñan o corrigen:** `pt_plan_topology`,
   `pt_full_build`, `pt_fix_plan`, `pt_explain_plan`, `pt_validate_plan`, `pt_generate_configs`,
   `pt_estimate_plan`, `pt_audit_security`, `pt_health_check` ni `pt_live_deploy`.
8. **Etiquetas: solo las de red** que dé el alumno. Nada de etiquetas de dispositivos, de IPs de
   interfaz, de "VLAN1" ni de SSID.

Tu valor está en hacer rápido y sin errores **lo mecánico**: escribir la configuración en el archivo,
cambiar tarjetas de red, configurar el Wi-Fi WPA2, colocar las etiquetas y lanzar los pings.

`SK` = carpeta de esta skill. En Windows usa `python`; en Linux o macOS, `python3`. Trabaja siempre en
una carpeta temporal y **nunca sobrescribas el archivo original del alumno**.

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

## 1. Leer la práctica (solo información, sin opinar)
```
python SK/scripts/ptcrypt.py d Lab.pka full.xml
python SK/scripts/pka_split.py split full.xml red.xml      # SOLO el 1er bloque (red del alumno)
python SK/scripts/pt_summary.py red.xml full.xml           # dispositivos, puertos, enlaces, notas, enunciado
```
`full.xml` no es XML válido (lleva bytes binarios), así que no lo abras entero con un parser.
Enseña al alumno **solo hechos de la topología**: dispositivos, interfaces que están conectadas y a
qué, notas que ya hay en el lienzo y el texto del enunciado. Sirve para que pueda referirse a cada
red o interfaz por su nombre. No digas cuántas subredes hacen falta ni de qué tamaño.

## 2. Leer el diseño del alumno (desde archivo, sin preguntar)
El alumno entrega su diseño en un archivo: la plantilla `SK/examples/plantilla_alumno.json` rellenada
(o un `plan.json`, o un texto/documento con sus datos). **Léelo; no se lo preguntes.** Lo que decide él
y debe contener el archivo es **solo** esto. Si falta algo, no sigas: informa de los campos que faltan
o están vacíos y termina.

| Dato (lo decide el alumno) | Ejemplo de forma (no de valor) |
|---|---|
| **Variables del enunciado** (`MN`, `NC`…) | `"MN": "6"` |
| **Grupos**: una LAN por cada interfaz de router. Red con prefijo, gateway y a qué router/interfaz va | `"G1": {"red": "a.b.c.d/nn", "gateway": "…", "router": "Router0", "interfaz": "GigabitEthernet0/0/0"}` |
| **Switches**: IP de cada uno (VLAN1), dentro de su grupo | `"switches": {"Switch1": "…"}` |
| **Hosts**: qué equipos van en cada grupo y **el rango de IPs** que les asigna | `"hosts": ["PC0","PC1"], "rango": [".2",".6"]` o `"rango": "libres"` |
| **Wi-Fi**: qué clientes van a cada AP | `"ap": "Access Point0", "clientes_wifi": ["PC6","PC7"]` |
| **Etiquetas de red**: texto o red de cada etiqueta nueva | `"etiqueta": "a.b.c.d/nn"` |
| Hostnames (opcional) y SSID/clave si los quiere fijar él | |

- Si el enunciado tiene variables como `MN` o `NC` y están vacías en el archivo, cuenta como dato
  que falta. Nunca las supongas.
- Si un dato es ambiguo (por ejemplo, "la red de la izquierda"), no adivines ni preguntes: lístalo
  como dato que falta o es ambiguo y termina.
- Si el alumno no ha hecho el subnetting o no ha elegido las redes, la respuesta es la regla 5.
- Pasar sus datos al formato JSON es trabajo mecánico y lo haces tú. Por ejemplo, escribir el nombre
  exacto de la interfaz. Lo que **no** cambias nunca es el valor. El formato completo está en
  `SK/examples/plan_formato.json`.
- **No le pidas** IPs de hosts una a una, IPs de los enlaces serie, rutas estáticas, SSID, claves ni
  dónde va cada etiqueta: eso lo calcula el paso 3.

## 3. Rellenar lo mecánico (sin preguntar nada)
```
python SK/scripts/pt_plan_auto.py red.xml diseno.json plan.json
```
Lee el diseño y la red del `.pka`, y escribe el `plan.json` que se aplica después. Rellena, con reglas
fijas y sin tocar ninguna decisión del alumno:
- **IP de cada host**: recorre el rango que dio él de menor a mayor, salta las que ya usan gateway,
  switches y APs, y asigna en el orden en que él lista los equipos del grupo.
- **IPs de los enlaces serie**: toma la red `/30` o `/31` de la etiqueta que ya está en el lienzo; el
  router cuyo nombre va primero se queda la dirección baja (`.1`) y el otro la siguiente.
- **Rutas estáticas**: camino más corto por los enlaces entre routers, con red destino y siguiente salto.
- **Wi-Fi**: si no dio SSID, `LAB-AP<n>`; si no dio clave, 12 caracteres al azar con mayúscula,
  minúscula y dígito (WPA2-PSK). Pasa a inalámbricos los equipos que estén a cable.
- **Etiquetas**: coloca cada una junto al router y el switch principal de su grupo.

Comprueba el resumen que imprime y sigue. Si un dato del alumno es incorrecto, **no lo corrijas**: se
aplica igual y lo descubre la verificación.

## 4. Aplicar y empaquetar
```
python SK/scripts/pt_apply_plan.py red.xml plan.json red_new.xml
python SK/scripts/pka_split.py merge full.xml red_new.xml full_new.xml
python SK/scripts/ptcrypt.py e full_new.xml Lab_configurado.pka
python SK/scripts/ptcrypt.py d Lab_configurado.pka check.xml        # comprobación de ida y vuelta
python SK/scripts/pka_split.py split check.xml chk.xml
python SK/scripts/pt_summary.py chk.xml
```
- `pt_apply_plan.py` **no valida el diseño**: aplica lo que pone el plan. Solo se detiene si el plan
  no se puede aplicar: un dispositivo o una interfaz que no existe, una IP mal escrita o una variable
  vacía.
- Si se detiene, díselo al alumno con la frase de la regla 4. Por ejemplo: "Has fallado en la
  interfaz Serial0/2/0 de Router0 porque ese router no tiene esa interfaz".
- Compara el resumen final con el diseño del alumno, línea a línea, para asegurarte de que **tú** has
  copiado bien sus datos. Si el error es tuyo, corrígelo: eso no es corregir al alumno.
- Guarda `<nombre>_configurado.pka` junto al original y comprueba el tamaño con `ls` o `dir`.

## 5. Verificar con pings (MCP packet-tracer)
1. Ejecuta `pt_bridge_status`. Si PT no está conectado, pide al alumno que abra PT y
   **Extensions → MCP BUILDER**. No lances PT tú.
2. `pt_open_project` **solo acepta `.pkt`**. Copia el `.pka` configurado a la carpeta temporal con
   extensión `.pkt` y ábrelo. Después ejecuta `pt_query_topology` y `pt_fast_forward`.
3. **Lanza los pings sin elegir a dedo** con `pt_verify_connectivity`:
   - un host de cada LAN contra un host de cada una de las otras LAN;
   - cada host contra su gateway;
   - un host contra la IP de cada switch;
   - un host contra cada interfaz serie;
   - todos los clientes Wi-Fi.

   Si un ping falla o pierde paquetes, **repítelo una vez**: el primero puede perderse por ARP o
   porque el Wi-Fi todavía se está asociando. Con 100 % de pérdida en el segundo intento, cuenta
   como fallo. Si pierde algunos paquetes pero llega alguno, cuenta como OK.
4. Para cada fallo, **averigua el motivo observado (Y)** solo leyendo:
   - `pt_send_pdu(source, destination, steps=10)`: en qué dispositivo muere el paquete y qué motivo
     da PT;
   - `pt_read_device_panel`: IP y gateway reales del host;
   - `pt_read_routes`;
   - `pt_inspect_ports`.

   **No cambies nada en PT.**
5. No digas que algo funciona si no has visto el ping responder.

## 6. Informe al alumno (en español)
- **Lo que se ha aplicado**: una tabla con sus propios datos (red, interfaces, rutas o protocolo,
  switches, hosts, SSID) y la ruta del `.pka` configurado.
- **Pings OK**: la lista.
- **Fallos**: uno por línea, cada uno con la frase completa de la regla 4. Ni una palabra más sobre
  cómo arreglarlo.
- Si no hay MCP, dale la lista exacta de pings para que los haga él (PC → Desktop → Command Prompt).

Cuando el alumno mande un diseño corregido, vuelve a aplicarlo **desde el archivo original** (paso 4)
y verifica otra vez (paso 5).

## Trampas técnicas conocidas (lo mecánico sí lo resuelves tú)
- Solo se edita el 1er `<PACKETTRACER5>`; el resto del archivo se copia byte a byte (`pka_split`).
- PT aplica la `RUNNINGCONFIG` al abrir. El script quita ` shutdown` en las interfaces que usa el plan.
- Hosts con IP estática: el script vacía `DHCP_CLIENT/PORT_DATA_MAP` y pone la IP en **todos** los
  perfiles Wi-Fi (`CURRENT_PROFILE` y `PROFILES`). Si no, PT pide DHCP al abrir y el host acaba con
  169.254.x.x (pasó con PC7 del Lab07). Si aun así un host sale con 169.254.x.x o 0.0.0.0, el problema
  es del script, no del alumno: revísalo antes de culpar al diseño.
- Cambiar la tarjeta de cable por una inalámbrica (`swap_to_wireless`) por XML es lo más frágil. Si un
  cliente no se asocia y su SSID y clave coinciden con las del AP, pide al alumno que cambie la tarjeta
  a mano (pestaña Physical, WPC300N o WMP300N).
- El MCP no puede configurar WPA en los clientes (solo desde la interfaz gráfica); por XML sí. No
  configures el Wi-Fi por MCP.
- `pt_plan_auto.py` **no valida** el diseño: si dos redes se solapan o un gateway no es de su red, lo
  aplica igual. Lo que falle lo destapan Packet Tracer y los pings, no tú antes de aplicar.
- El `.pka` no guarda IP en los APs (`AccessPoint-PT`): si el alumno asigna IP a un AP, no hay dónde
  ponerla. De un AP solo se configuran SSID y clave.
- Cifrado: `ptcrypt.py` usa la extensión C de Twofish si la hay (Linux) y, si no, `lib/twofish_py.py`
  en Python puro (Windows; tarda unos 3 s por archivo).
- Detalle del formato XML: [reference/xml-format.md](reference/xml-format.md).
