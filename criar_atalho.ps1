# Cria atalho na Área de trabalho e no menu Iniciar (só neste PC).
$ErrorActionPreference = "Stop"
$pasta = Split-Path -Parent $MyInvocation.MyCommand.Path
$vbs = Join-Path $pasta "abrir.vbs"
$nome = "Finaud Serviços locais"
$wscript = Join-Path $env:SystemRoot "System32\wscript.exe"
$icone = "$env:SystemRoot\System32\imageres.dll,109"

function Novo-Atalho([string]$destino) {
    $ws = New-Object -ComObject WScript.Shell
    $atalho = $ws.CreateShortcut($destino)
    $atalho.TargetPath = $wscript
    $atalho.Arguments = "`"$vbs`""
    $atalho.WorkingDirectory = $pasta
    $atalho.WindowStyle = 7
    $atalho.Description = "Liga e desliga os sistemas Finaud neste PC"
    $atalho.IconLocation = $icone
    $atalho.Save()
}

$area = Join-Path ([Environment]::GetFolderPath("Desktop")) "$nome.lnk"
$menu = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs\$nome.lnk"
Novo-Atalho $area
Novo-Atalho $menu
Write-Output $area
Write-Output $menu
