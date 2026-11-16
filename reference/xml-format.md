# Formato XML de Packet Tracer 9 (medido en PT 9.0.1)

## Estructura de un .pka descifrado
```
<PACKETTRACER5_ACTIVITY>
  <VERSION>
  <PACKETTRACER5>   ← 1º: red del ALUMNO (la que se edita y se ve al abrir)
  <PACKETTRACER5>   ← 2º: red de respuesta (answer network)
  <PACKETTRACER5>   ← 3º: red inicial / plantilla
  <COMPARISONS> <INITIALSETUP> <OPTIONS>
  <VARIABLE_MANAGER> ← contiene bytes binarios → el archivo entero NO es XML válido
  <INSTRUCTIONS><PAGE><![CDATA[ enunciado en HTML ]]>
```
Un `.pkt` normal tiene solo un `<PACKETTRACER5>` (sin `_ACTIVITY`).

## Dispositivo
`NETWORK/DEVICES/DEVICE/ENGINE`: `TYPE@model`, `NAME`, `MODULE/SLOT/MODULE/PORT…`, `SAVE_REF_ID`,
`SYS_NAME`, `RUNNINGCONFIG/LINE*`, `STARTUPCONFIG/LINE*`, `GATEWAY` (hosts).
Posición en el lienzo lógico: `DEVICE/WORKSPACE/LOGICAL/X|Y` (esquina superior izquierda del icono).

## Routers y switches IOS
- **PT ejecuta la `RUNNINGCONFIG` al cargar**: es la fuente de verdad. Las rutas estáticas solo existen ahí
  (`ip route …` justo después de `ip classless`). Los bloques `router ospf|rip|eigrp …` van justo
  **antes** de `ip classless` (donde los escribe IOS).
- Además poner `IP`, `SUBNET`, `POWER=true` en el `PORT` correspondiente (orden de los PORT físicos =
  orden de `interface …` físicas en la config). ISR4331: G0/0/0, G0/0/1, G0/0/2, S0/1/0, S0/1/1.
- Switch 2960: IP en `interface Vlan1` y `ip default-gateway X` tras ese bloque. No hay PORT para Vlan1.
- `STARTUPCONFIG` vacío = nunca se hizo `write memory`; copiar ahí la running-config.

## Hosts (PC-PT, Laptop-PT)
`PORT/IP`, `PORT/SUBNET`, `PORT/PORT_GATEWAY`, `PORT/PORT_DHCP_ENABLE=false`, y `ENGINE/GATEWAY`.

**Trampa (medida en el Lab07, PC7):** aunque `PORT_DHCP_ENABLE=false`, si
`ENGINE/DHCP_CLIENT/PORT_DATA_MAP` contiene un `<PORT_DATA_ENTRY><PORT>Wireless0</PORT>…`, PT arranca
el cliente DHCP en ese puerto al abrir y el host acaba con `0.0.0.0` o `169.254.x.x`. Para IP
estática hay que vaciar ese `PORT_DATA_MAP` (lo hace `pt_apply_plan.py`).

## Tarjetas de red
| Equipo | Slot `TYPE` | Cable | Inalámbrica |
|---|---|---|---|
| PC-PT | `ePtHostModule` | `PT-HOST-NM-1CFE` | `Linksys-WMP300N` |
| Laptop-PT | `ePtLaptopModule` | `PT-LAPTOP-NM-1CFE` | `Linksys-WPC300N` |
Puerto inalámbrico: `PORT/TYPE = eHostWirelessN`, `BANDWIDTH 54000`.

## Wi-Fi
AP (`AccessPoint-PT`): `ENGINE/WIRELESS_SERVER/WIRELESS_COMMON`.
Cliente: `ENGINE/WIRELESS_CLIENT/WIRELESS_COMMON` + `CURRENT_PROFILE/WIRELESS_PROFILE`.
```
<SSID>…</SSID>
<ENCRYPT_TYPE>4</ENCRYPT_TYPE>   4 = AES
<AUTHEN_TYPE>4</AUTHEN_TYPE>     0 abierto · 4 WPA2-PSK · 5 WPA2 (RADIUS)
<STANDARD_CHANNEL>…</STANDARD_CHANNEL>
<WEP_PROCESS><KEY>clave</KEY><USERID/><PASSWORD/><ENCRYPTION>4</ENCRYPTION></WEP_PROCESS>
```
Perfil del cliente: `SSID`, `NETWORK_TYPE 3`, `AUTHEN_TYPE 4`, `ENCRYPT_TYPE 4`, `WEP_KEY`,
`DHCP_ENABLED 0`, `IP_ADDRESS`, `SUBNET_MASK`, `DEFAULT_GATEWAY`.
**Trampa:** además del `CURRENT_PROFILE` puede haber perfiles guardados en `WIRELESS_CLIENT/PROFILES`
(p. ej. uno `Default` con `DHCP_ENABLED 1`). Hay que aplicar los mismos valores a **todos** los
`WIRELESS_PROFILE` del cliente.
(El MCP de Packet Tracer **no** puede poner WPA en clientes; por XML sí.)

## Enlaces
`NETWORK/LINKS/LINK/CABLE`: `FROM`/`TO` (= `SAVE_REF_ID`), dos `PORT`, y en serie `DCEDEV`/`DCEPORT`.

## Notas (etiquetas del lienzo)
```
<NOTE uuid="{…}"><X/><Y/><Z/><TEXT translate="true">172.22.0.0/18</TEXT>
<NOTECLUSTERID>1-1</NOTECLUSTERID><MEM_ADDR>número</MEM_ADDR></NOTE>
```
