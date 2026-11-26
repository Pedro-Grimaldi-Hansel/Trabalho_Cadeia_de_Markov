# Executa o projeto com Python 3.10 ou superior.
[CmdletBinding()]
param(
    [switch] $Testes,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $ArgumentosPython
)

$ErrorActionPreference = 'Stop'
$taskPython = $null
$taskPrefixo = @()
$taskVenv = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $taskVenv) {
    $taskPython = $taskVenv
}
if (-not $taskPython) {
    $taskArquivoLocal = Join-Path $PSScriptRoot 'python-local.txt'
    if (Test-Path -LiteralPath $taskArquivoLocal) {
        $taskCaminhoLocal = (Get-Content -LiteralPath $taskArquivoLocal -Raw).Trim()
        if (Test-Path -LiteralPath $taskCaminhoLocal -PathType Leaf) {
            $taskPython = $taskCaminhoLocal
        }
    }
}
if (-not $taskPython) {
    $taskPyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($taskPyLauncher) {
        $taskPython = $taskPyLauncher.Source
        $taskPrefixo = @('-3')
    }
}
if (-not $taskPython) {
    $taskComando = Get-Command python -ErrorAction SilentlyContinue
    # O alias da Microsoft Store não garante uma instalação funcional.
    if ($taskComando -and $taskComando.Source -notmatch '\\Microsoft\\WindowsApps\\python.exe$') {
        $taskPython = $taskComando.Source
    }
}
if (-not $taskPython) {
    throw 'Python 3.10 ou superior nao encontrado. Instale o Python e execute: python -m src.main'
}

Push-Location -LiteralPath $PSScriptRoot
try {
    & $taskPython @taskPrefixo -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Este projeto requer Python 3.10 ou superior.' }
    if (-not $ArgumentosPython) { $ArgumentosPython = @() }
    if ($Testes) {
        & $taskPython @taskPrefixo -X utf8 -m unittest discover -s tests -v
    } else {
        & $taskPython @taskPrefixo -X utf8 -m src.main @ArgumentosPython
    }
    $taskCodigoSaida = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $taskCodigoSaida
