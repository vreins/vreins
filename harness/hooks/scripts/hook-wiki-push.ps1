<#
  hook-wiki-push.ps1  —  승인받은 산출물이 내 PC 에만 남는 것을 막는다

  2026-10-27. 측정 중에 드러났다 — 위키 저장소가 **ahead 15** 였고 가장 오래된 것이
  일주일 묵어 있었다. 단계별 커밋은 정확히 찍혀 있었다(01 들인다 → 02 들인다 → ...).
  커밋은 돌고 푸시만 한 번도 안 일어났다.

  원인은 고장이 아니라 **빠진 것**이었다. SKILL.md 단계 종료 순서가 「3 승인 후
  커밋한다」로 끝났고, 푸시하라는 말이 하네스 어디에도 없었다. 모델은 3번까지
  하고 할 일을 다 한 것이다. 사람은 「커밋했다」를 「위키에 올라갔다」로 읽었다.

  그래서 SKILL.md 에 푸시를 적었다. 그것만으로는 약하다 —
  **커밋은 실패하면 보이고 푸시는 실패해도 조용하다.** 사내망 밖이면 그냥 안 된다.
  한 번 조용히 실패하면 그 뒤로 계속 쌓이고, 쌓이는 것을 아무도 안 본다.

  그래서 이 훅이 센다.

  -Mode Baseline   SessionStart. 들어올 때의 위키 HEAD 를 적어 둔다
  -Mode Check      Stop. 이 세션이 커밋했는데 안 올렸으면 막는다

  **이 세션이 만든 커밋만 본다.** 남이 쌓아 둔 ahead 로 잔소리하지 않는다 —
  들어올 때 HEAD 가 그대로면 이 세션은 커밋한 적이 없는 것이다.

  **세션당 한 번만 막는다.** 푸시가 환경 탓에 안 되는 자리(사내망 밖)에서
  영원히 못 끝내면 훅이 일을 막는 것이 된다. 한 번 알렸으면 사람이 안다.

  실패해도 항상 통과시킨다. 훅이 세션을 가두면 안 된다.

  주의 — 이 파일은 반드시 UTF-8 BOM 으로 저장한다 (hook-common.ps1 머리말 참조).
#>
param([ValidateSet('Baseline', 'Check')][string]$Mode = 'Check')

$ErrorActionPreference = 'Continue'

. (Join-Path $PSScriptRoot 'lib\hook-common.ps1')

# --- 들어온 것 읽기 -----------------------------------------------------------
# 훅 입력은 stdin 의 JSON 이다. 못 읽어도 멈추지 않는다 — 세션 구분만 못 할 뿐이다.
$sid = 'nosession'
$stopActive = $false
try {
  $raw = [Console]::In.ReadToEnd()
  if ($raw) {
    $j = $raw | ConvertFrom-Json
    if ($j.session_id)       { $sid = [string]$j.session_id }
    if ($j.stop_hook_active) { $stopActive = [bool]$j.stop_hook_active }
  }
} catch { }

$stateDir = Join-Path $env:TEMP 'vreins-hooks'
$headFile = Join-Path $stateDir ($sid + '.wikihead')
$doneFile = Join-Path $stateDir ($sid + '.wikipush-told')

function Invoke-Git {
  <#
    출력만 받는다. 실패는 $null 로 돌려 호출부가 「모른다」로 다루게 한다.

    파라미터 이름이 $GitArgs 인 이유 — $Args 는 PowerShell 자동 변수라
    param 으로 쓰면 바인딩이 조용히 비고 git 이 인자 없이 돈다. 한 번 당했다.
  #>
  param([string[]]$GitArgs)
  try {
    $out = & git @GitArgs 2>$null
    if ($LASTEXITCODE -ne 0) { return $null }
    return ($out | Out-String).Trim()
  } catch { return $null }
}

$wiki = Get-VreinsWikiRoot
if (-not $wiki -or -not (Test-Path $wiki)) { exit 0 }

# 위키가 git 저장소가 아니면(실습 위키가 그렇다) 볼 것이 없다.
if (-not (Invoke-Git @('-C', $wiki, 'rev-parse', '--is-inside-work-tree'))) { exit 0 }

$head = Invoke-Git @('-C', $wiki, 'rev-parse', 'HEAD')
if (-not $head) { exit 0 }

# --- Baseline — 들어올 때의 HEAD 를 적어 둔다 ---------------------------------
if ($Mode -eq 'Baseline') {
  try {
    if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Path $stateDir -Force | Out-Null }
    Set-Content -Path $headFile -Value $head -Encoding ASCII
    if (Test-Path $doneFile) { Remove-Item $doneFile -Force }
  } catch { }

  <#
    들어올 때 이미 밀려 있으면 **그 자리에서 알린다.** 막지는 않는다 —
    남이 쌓아 둔 것이지 이 세션의 잘못이 아니다. 다만 모르고 그 위에
    또 쌓는 것을 막아야 한다. SessionStart 의 stdout 은 모델에 닿는다.
  #>
  $ahead = Invoke-Git @('-C', $wiki, 'rev-list', '--count', '@{u}..HEAD')
  if ($ahead -and [int]$ahead -gt 0) {
    $oldest = Invoke-Git @('-C', $wiki, 'log', '--format=%ad', '--date=short', '@{u}..HEAD')
    $since  = if ($oldest) { ($oldest -split "`n")[-1].Trim() } else { '?' }
    Write-Output '===== 위키에 안 올라간 커밋이 있다 ====='
    Write-Output ''
    Write-Output ('  안 올라간 커밋   ' + $ahead + '개')
    Write-Output ('  가장 오래된 것   ' + $since)
    Write-Output ''
    Write-Output '**안 올라간 산출물은 없는 산출물이다.** 승인까지 받은 문서가'
    Write-Output '내 PC 에만 있으면 아무도 못 본다. 사용자에게 알리고 올릴지 묻는다.'
    Write-Output ''
    Write-Output '  git -C {위키} log --oneline @{u}..HEAD    무엇이 밀렸는지 먼저 보여준다'
    Write-Output ''
    Write-Output '내용을 안 보고 밀지 않는다 — 실습용·측정용 커밋이 섞여 있을 수 있다.'
    Write-Output ''
  }
  exit 0
}

# --- Check — 이 세션이 커밋했는데 안 올렸나 -----------------------------------
if ($stopActive) { exit 0 }          # 이미 한 번 막았다
if (Test-Path $doneFile) { exit 0 }  # 이 세션에 이미 알렸다

$base = $null
if (Test-Path $headFile) { try { $base = (Get-Content $headFile -Raw).Trim() } catch { } }

# 들어올 때와 HEAD 가 같으면 이 세션은 커밋한 적이 없다. 볼 것 없다.
if ($base -and $base -eq $head) { exit 0 }

# baseline 을 못 읽었으면 판단하지 않는다 — 남의 ahead 로 막으면 안 된다.
if (-not $base) { exit 0 }

$ahead = Invoke-Git @('-C', $wiki, 'rev-list', '--count', '@{u}..HEAD')
if (-not $ahead -or [int]$ahead -le 0) { exit 0 }   # 다 올라갔거나 upstream 이 없다

try {
  if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Path $stateDir -Force | Out-Null }
  Set-Content -Path $doneFile -Value '1' -Encoding ASCII
} catch { }

$reason = @(
  "이 세션이 위키에 커밋했는데 올리지 않았다 — 안 올라간 커밋 $ahead 개.",
  "",
  "단계 종료 순서 3번은 **푸시까지**다(vreins-workflow SKILL.md).",
  "커밋은 내 PC 안의 일이라 거기서 멈추면 승인받은 산출물을 아무도 못 본다.",
  "위키 푸시는 커밋 승인에 들어 있으므로 따로 승인을 받지 않는다.",
  "",
  "  git -C `"$wiki`" push",
  "",
  "푸시가 실패하면 — 사내망 밖이거나 upstream 이 없거나 거절당했으면 —",
  "그 사실을 사용자에게 **그대로 보고한다.** 혼자 --force 하거나 remote 를",
  "바꾸지 않는다. 커밋은 남아 있으니 올릴 수 있을 때 올리면 된다.",
  "",
  "올리면 안 되는 커밋이면(실습·측정용) 그렇게 말하고 넘어가도 된다.",
  "이 검사는 세션당 한 번만 막는다."
) -join "`n"

@{ decision = 'block'; reason = $reason } | ConvertTo-Json -Compress
exit 0
