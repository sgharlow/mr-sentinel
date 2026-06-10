<#
.SYNOPSIS
  Repeatable screen-capture of the 3 manual demo clips (C1 trace, C4 GitLab diff,
  C5 GitLab comment) using ffmpeg's Windows screen grabber (gdigrab) — no OBS needed.

  Same script for the TEST RUN and the REAL TAKE:
    .\scripts\record-clips.ps1 -Clip C1 -Test     # rehearsal -> clips/C1-trace-TEST.mp4
    .\scripts\record-clips.ps1 -Clip C1           # real take -> clips/C1-trace.mp4
    .\scripts\record-clips.ps1 -Clip all          # C1 then C4 then C5, in order
    .\scripts\record-clips.ps1 -Clip C1 -AutoKey  # also auto-press F11 + replay (R)

  How it works: opens the surface, gives you a countdown to get ready (log in / focus),
  then records the PRIMARY monitor for the clip's duration and writes a 1920x1080 mp4.
  You perform the on-screen actions during the recording window (scroll, etc.).
  -AutoKey attempts the keypresses for you (F11 fullscreen, R replay for C1,
  Page-Down auto-scroll for C4/C5) — convenience only; manual still works if it misfires.

.NOTES
  Output: docs\demo\clips\<name>.mp4   (these are gitignored working files)
  Silent by design (no audio) — narration is recorded separately.
#>
param(
  [ValidateSet('C1','C4','C5','all')][string]$Clip = 'all',
  [int]$Countdown = 6,
  [switch]$Test,
  [switch]$AutoKey
)

$ErrorActionPreference = 'Stop'
$repo  = Split-Path -Parent $PSScriptRoot
$demo  = Join-Path $repo 'docs\demo'
$clips = Join-Path $demo 'clips'
$trace = Join-Path $demo 'agent-trace.html'
New-Item -ItemType Directory -Force -Path $clips | Out-Null

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw "ffmpeg not on PATH. Install it or add it to PATH." }
Add-Type -AssemblyName System.Windows.Forms
$ws = New-Object -ComObject WScript.Shell

# Primary monitor geometry (capture just this screen)
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds

# Clip definitions ------------------------------------------------------------
$DEFS = @{
  C1 = @{ name='C1-trace'; dur=16; title='MR Sentinel';
          surface=$trace; isFile=$true;
          steps=@('F11 = full-screen','When RECORDING starts: press R to replay the log reveal',
                  'Watch the 3 [GitLab MCP] tool-call lines + the red block verdict appear') }
  C4 = @{ name='C4-gitlab-diff'; dur=20; title='chore: add .env';
          surface='https://gitlab.com/sgharlow/governance-demo-app/-/merge_requests/10/diffs'; isFile=$false;
          steps=@('LOG IN to gitlab.com first (anon is sign-in-walled)','F11 = full-screen',
                  'Ensure .env.production is expanded','During RECORDING: slow-scroll; pause ~1s on AWS_ACCESS_KEY_ID') }
  C5 = @{ name='C5-gitlab-comment'; dur=26; title='chore: add .env';
          surface='https://gitlab.com/sgharlow/governance-demo-app/-/merge_requests/10'; isFile=$false;
          steps=@('LOG IN to gitlab.com first','F11 = full-screen','Scroll to the MR Sentinel comment',
                  'During RECORDING: pan badge -> evidence -> linked issue -> blocked-compliance label',
                  '(Optional clip — you can use C3-audit.mp4 for Shot E instead)') }
}

function Record-One($key) {
  $d = $DEFS[$key]
  $suffix = if ($Test) { '-TEST' } else { '' }
  $out = Join-Path $clips ("{0}{1}.mp4" -f $d.name, $suffix)

  Write-Host "`n========== $key  ($($d.name), $($d.dur)s) ==========" -ForegroundColor Cyan
  Write-Host "Surface: $($d.surface)"
  Write-Host "Do this:" -ForegroundColor Yellow
  $d.steps | ForEach-Object { Write-Host "   - $_" }
  Write-Host "Output : $out"

  # open the surface
  Start-Process $d.surface | Out-Null
  Start-Sleep -Seconds 2

  # countdown to get ready (log in / click the page / press F11 to fullscreen)
  Write-Host "  >> CLICK the page, then press F11 (fullscreen) during this countdown <<" -ForegroundColor Yellow
  [console]::Beep(660,150)
  for ($i = $Countdown; $i -ge 1; $i--) { Write-Host ("  starting in {0}..." -f $i) -ForegroundColor DarkGray; Start-Sleep -Seconds 1 }

  # build ffmpeg gdigrab args -> normalize to 1920x1080 letterboxed
  $vf = 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2'
  # Capture the FULL desktop (physical pixels) and scale to 1920x1080 — robust to DPI
  # scaling (a 1920x1080 panel at 125% reports 1536x864 logical; gdigrab grabs physical).
  $args = @('-y','-f','gdigrab','-framerate','30',
            '-i','desktop','-t',$d.dur,'-vf',$vf,'-c:v','libx264','-pix_fmt','yuv420p','-preset','veryfast',$out)

  [console]::Beep(900,250)   # BEEP = recording started -> begin your slow scroll
  Write-Host ">>> RECORDING $($d.dur)s — go! (scroll slowly; pause on the key line)" -ForegroundColor Green
  $proc = Start-Process -FilePath ffmpeg -ArgumentList $args -PassThru -WindowStyle Hidden

  if ($AutoKey) {
    Start-Sleep -Milliseconds 500
    [void]$ws.AppActivate($d.title)
    Start-Sleep -Milliseconds 400
    $ws.SendKeys('{F11}'); Start-Sleep -Milliseconds 900
    if ($key -eq 'C1') {
      $ws.SendKeys('r')                                  # replay the reveal
    } else {
      $ticks = [int]([math]::Floor($d.dur / 6.0))        # gentle auto-scroll (~every 6s)
      for ($t=0; $t -lt $ticks; $t++) { Start-Sleep -Seconds 6; [void]$ws.AppActivate($d.title); $ws.SendKeys('{PGDN}') }
    }
  }

  $proc | Wait-Process -Timeout ($d.dur + 20)
  [console]::Beep(450,400)   # BEEP = recording stopped
  if (Test-Path $out) {
    $sz = [math]::Round((Get-Item $out).Length/1MB,2)
    Write-Host "DONE -> $out  (${sz} MB)" -ForegroundColor Green
  } else { Write-Host "WARN: no output written ($out)" -ForegroundColor Red }
}

$order = if ($Clip -eq 'all') { @('C1','C4','C5') } else { @($Clip) }
Write-Host ("Mode: {0} | clips: {1} | countdown: {2}s | autokey: {3}" -f `
  ($(if($Test){'TEST'}else{'REAL'})), ($order -join ','), $Countdown, [bool]$AutoKey) -ForegroundColor Magenta
foreach ($k in $order) {
  Record-One $k
  if ($order.Count -gt 1 -and $k -ne $order[-1]) { Read-Host "`nPress ENTER for the next clip" | Out-Null }
}
Write-Host "`nAll requested clips captured. Preview them in $clips, then assemble per docs\video-finish-checklist.md." -ForegroundColor Cyan
