# Instalador de dependencias de la skill packet-tracer-lab (Windows 10/11).
#
# El agente SOLO lo ejecuta despues de pedir permiso al alumno.
#   powershell -ExecutionPolicy Bypass -File setup_windows.ps1
#
# Cada paso se salta si ya esta hecho. No instala Cisco Packet Tracer (requiere cuenta NetAcad).
# Pasos: Python 3.12 -> uv -> lxml -> MCP packet-tracer en Claude Code -> skill del MCP
#        -> extension MCP-Control-Center.pts en Packet Tracer.

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
function Step($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "    OK  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "    !!  $m" -ForegroundColor Yellow }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User") + ";" +
                "$env:USERPROFILE\.local\bin"
}
function Have($c) { [bool](Get-Command $c -ErrorAction SilentlyContinue) }
$hasWinget = Have "winget"

# ---------- 1. Python
Step "Python 3"
$py = $null
foreach ($c in @("python", "py")) {
    if (Have $c) {
        $v = & $c --version 2>&1
        if ($v -match "Python 3\.(\d+)" -and [int]$Matches[1] -ge 8) { $py = $c; break }
    }
}
if (-not $py) {
    if ($hasWinget) {
        winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
        Refresh-Path
        if (Have "python") { $py = "python" } elseif (Have "py") { $py = "py" }
    } else { Warn "No hay winget. Instala Python 3.12 desde https://www.python.org/downloads/ (marca 'Add to PATH')." }
}
if ($py) { Ok "$py -> $(& $py --version 2>&1)" } else { Warn "Python no disponible todavia (abre una terminal nueva y repite)." }

# ---------- 2. uv / uvx
Step "uv (lanza el servidor MCP)"
Refresh-Path
if (-not (Have "uvx")) {
    if ($hasWinget) {
        winget install -e --id astral-sh.uv --scope user --accept-package-agreements --accept-source-agreements
    }
    Refresh-Path
    if (-not (Have "uvx")) {
        powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
        Refresh-Path
    }
}
if (Have "uvx") { Ok "uvx -> $((Get-Command uvx).Source)" } else { Warn "uv no se pudo instalar." }

# ---------- 3. lxml (opcional)
Step "lxml (opcional)"
if ($py) {
    & $py -c "import lxml" 2>$null
    if ($LASTEXITCODE -ne 0) { & $py -m pip install --user --quiet lxml }
    & $py -c "import lxml" 2>$null
    if ($LASTEXITCODE -eq 0) { Ok "lxml" } else { Warn "lxml no instalado (no es imprescindible)." }
}

# ---------- 4. MCP packet-tracer en Claude Code
Step "MCP packet-tracer en Claude Code"
if (Have "claude") {
    $list = (claude mcp list 2>&1) | Out-String
    if ($list -match "packet-tracer") { Ok "ya registrado" }
    else {
        # en PowerShell el separador -- va entre comillas
        claude mcp add --scope user --transport stdio packet-tracer "--" uvx packet-tracer-mcp --stdio
        if ($LASTEXITCODE -eq 0) { Ok "registrado (reinicia Claude Code para cargarlo)" } else { Warn "fallo al registrar el MCP" }
    }
} else { Warn "No se encontro 'claude'. Registra a mano en tu agente: uvx packet-tracer-mcp --stdio" }

# ---------- 5. Skill del MCP (guia de las herramientas pt_*)
Step "Skill 'packet-tracer' del MCP"
if (Test-Path "$env:USERPROFILE\.claude\skills\packet-tracer\SKILL.md") { Ok "ya instalada" }
elseif (Have "uvx") {
    uvx packet-tracer-mcp install-skill
    if ($LASTEXITCODE -eq 0) { Ok "instalada" } else { Warn "no se pudo instalar la skill del MCP" }
}

# ---------- 6. Extension MCP-Control-Center.pts
Step "Extension de Packet Tracer (MCP-Control-Center.pts)"
$dl = Join-Path $env:USERPROFILE "Downloads"
$pts = Join-Path $dl "MCP-Control-Center.pts"
if (-not (Test-Path $pts)) {
    try {
        Invoke-WebRequest -UseBasicParsing -OutFile $pts `
            -Uri "https://github.com/Mats2208/MCP-Packet-Tracer/releases/latest/download/MCP-Control-Center.pts"
        Ok "descargada en $pts"
    } catch { Warn "No se pudo descargar. Bajala de https://github.com/Mats2208/MCP-Packet-Tracer/releases/latest" }
} else { Ok "ya descargada: $pts" }

$ptDirs = @(Get-ChildItem "C:\Program Files\Cisco Packet Tracer*", "C:\Program Files (x86)\Cisco Packet Tracer*" `
            -Directory -ErrorAction SilentlyContinue)
if ($ptDirs.Count -eq 0) {
    Warn "Cisco Packet Tracer NO esta instalado. Instalalo a mano (necesita cuenta NetAcad): https://www.netacad.com/resources/lab-downloads"
} elseif (Test-Path $pts) {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
    foreach ($d in $ptDirs) {
        $dest = Join-Path $d.FullName "extensions\MCPControlCenter"
        if (Test-Path (Join-Path $dest "MCP-Control-Center.pts")) { Ok "ya copiada en $dest"; continue }
        if ($isAdmin) {
            New-Item -ItemType Directory -Force -Path $dest | Out-Null
            Copy-Item $pts $dest -Force
            Ok "copiada en $dest"
        } else {
            Warn "Sin permisos de administrador para copiar en $($d.FullName)."
            Warn "Alternativa: en Packet Tracer -> Extensions -> Scripting -> Configure PT Script Modules -> Add... -> $pts"
        }
    }
}

Write-Host "`nListo. Pasos manuales que quedan:" -ForegroundColor Cyan
Write-Host "  1. Reinicia Claude Code (para cargar el MCP)."
Write-Host "  2. Abre Packet Tracer: acepta 'enable new script module' y abre Extensions -> MCP BUILDER."
Write-Host "  3. Vuelve a comprobar:  python scripts\check_setup.py"
