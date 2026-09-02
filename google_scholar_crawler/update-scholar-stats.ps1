# Refresh the Google Scholar numbers the homepage reads, from this machine.
#
# The GitHub Actions runners cannot do this: Google answers their datacentre
# IPs with a flat HTTP 403, which is what left the nightly job failing for
# over a month. A residential connection gets served normally, so the crawl
# runs here on a weekly scheduled task and force-pushes the two JSON files to
# the google-scholar-stats branch, exactly as the workflow used to.
#
# Registered as the scheduled task "Update Scholar stats". Run it by hand with:
#   powershell -ExecutionPolicy Bypass -File <this file>
# Every run overwrites <LocalAppData>\scholar-stats-publish\last-run.log.

$ErrorActionPreference = 'Stop'

$crawler = $PSScriptRoot
$publish = Join-Path $env:LOCALAPPDATA 'scholar-stats-publish'
$remote = 'https://github.com/JinxiongCheng/JinxiongCheng.github.io.git'
$log = Join-Path $publish 'last-run.log'

New-Item -ItemType Directory -Force -Path $publish | Out-Null
Set-Content -Path $log -Value '' -Encoding utf8

function Write-Log($message) {
    $line = "[$(Get-Date -Format s)] $message"
    Write-Output $line
    Add-Content -Path $log -Value $line -Encoding utf8
}

# Windows PowerShell turns anything a native command writes to stderr into a
# terminating error while ErrorActionPreference is Stop -- and git reports a
# perfectly successful push on stderr. The exit code is the only honest
# signal, so every external call goes through here.
function Invoke-Native {
    param([string]$Exe, [string[]]$Arguments)

    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $output = & $Exe @Arguments 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous

    return [pscustomobject]@{ Output = ($output -join ' | '); ExitCode = $code }
}

function Invoke-Step($Label, $Exe, $Arguments) {
    $result = Invoke-Native -Exe $Exe -Arguments $Arguments
    if ($result.ExitCode -ne 0) {
        Write-Log "$Label output: $($result.Output)"
        throw "$Label failed (exit $($result.ExitCode))"
    }
    return $result
}

try {
    if (-not $env:GOOGLE_SCHOLAR_ID) { $env:GOOGLE_SCHOLAR_ID = 'uTVw50sAAAAJ' }

    # The task starts from the machine environment, which does not carry
    # whatever an interactive shell had; find the two tools explicitly.
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User')

    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python -or -not (Test-Path $python)) {
        $python = 'C:\Users\JinxiongCheng\anaconda3\python.exe'
    }
    if (-not (Test-Path $python)) { throw "no python found (looked for $python)" }

    $git = (Get-Command git -ErrorAction SilentlyContinue).Source
    if (-not $git -or -not (Test-Path $git)) { $git = "$env:ProgramFiles\Git\cmd\git.exe" }
    if (-not (Test-Path $git)) { throw "no git found (looked for $git)" }

    Write-Log "python: $python"
    Write-Log "git:    $git"
    Write-Log "crawling Scholar profile $env:GOOGLE_SCHOLAR_ID"

    Set-Location $crawler
    # A non-zero exit here means Google refused us; stopping leaves the
    # published numbers as they are rather than blanking the page.
    Invoke-Step 'crawl' $python @('main.py') | Out-Null

    $data = Get-Content (Join-Path $crawler 'results\gs_data.json') -Raw | ConvertFrom-Json
    Write-Log "got $($data.citedby) citations, h-index $($data.hindex)"

    # A throwaway history, force-pushed: the branch only ever holds these two
    # files, so there is nothing to preserve and nothing that can diverge.
    if (-not (Test-Path (Join-Path $publish '.git'))) {
        Invoke-Step 'git init' $git @('-C', $publish, 'init', '-q') | Out-Null
    }
    Copy-Item (Join-Path $crawler 'results\gs_data.json') $publish -Force
    Copy-Item (Join-Path $crawler 'results\gs_data_shieldsio.json') $publish -Force

    Invoke-Step 'git add' $git @('-C', $publish, 'add', '-A') | Out-Null
    Invoke-Step 'git commit' $git @(
        '-C', $publish,
        '-c', 'user.name=Jinxiong Cheng',
        '-c', 'user.email=xiongc729@gmail.com',
        'commit', '-q', '-m', 'Updated citation data', '--allow-empty') | Out-Null
    Invoke-Step 'git push' $git @(
        '-C', $publish, 'push', '--force', $remote, 'HEAD:google-scholar-stats') | Out-Null

    Write-Log 'published to google-scholar-stats'
    exit 0
}
catch {
    Write-Log "FAILED: $($_.Exception.Message)"
    Write-Log "at: $($_.InvocationInfo.PositionMessage -replace '\r?\n', ' ')"
    exit 1
}
