<#
  hook-inject-rule.ps1
  hooks\rules\{이름}.md 의 전문을 내보낸다. 요약하지 않는다.

  **내는 모양이 셋이다. 훅 이벤트가 정한다.**

    (기본)                표준출력. stdout 이 모델 컨텍스트로 가는 이벤트
                          (SessionStart · UserPromptSubmit 계열)에서만 뜻이 있다.
    -AsAdditionalContext  PreToolUse JSON 의 additionalContext. 조용히 모델에만 닿는다.
                          사용자에게 묻지 않는다 — 막을 일이 아닌 조언용.
    -AsPermissionAsk      PreToolUse JSON 의 permissionDecision: ask. 승인 창이 뜬다.
                          **정말로 막아야 하는 것**에만 쓴다.

  **PreToolUse 의 stdout 은 모델에 닿지 않는다.** exit 0 의 stdout 이 컨텍스트로
  들어가는 것은 SessionStart · UserPromptSubmit 계열뿐이고 PreToolUse · Stop 은
  사용자 transcript 에만 보인다. 그래서 PreToolUse 에 이 스크립트를 걸 때는
  **반드시 둘 중 하나를 준다.** 안 주면 돌기는 돌고 아무에게도 안 닿는다 —
  막지 못하면서 초록불을 켜는 검사가 제일 해롭다.

  두 JSON 모양 다 hookEventName 을 'PreToolUse' 로 박는다. 다른 이벤트에 걸면
  Claude Code 가 event_mismatch 로 **조용히 버린다** — 그때는 여기를 고쳐야 한다.

  사용
    hook-inject-rule.ps1 -Files read-before-work,no-credentials-in-docs -AsAdditionalContext -OncePerSession
    hook-inject-rule.ps1 -Files approval-before-commit -OnlyIfInputMatches "git commit" -AsPermissionAsk

  주의 — 이 파일은 반드시 UTF-8 BOM 으로 저장한다 (lib\hook-common.ps1 머리말 참조).
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string[]] $Files,

  # 훅 입력(JSON)에서 이 정규식이 걸릴 때만 주입한다. 비우면 항상 주입한다.
  [string] $OnlyIfInputMatches = '',

  # PreToolUse 의 additionalContext 로 낸다. 모델에만 닿고 사용자에게 묻지 않는다.
  [switch] $AsAdditionalContext,

  # PreToolUse 의 permissionDecision: ask 로 낸다. 사용자에게 승인 창이 뜬다.
  [switch] $AsPermissionAsk,

  <#
    한 세션에 한 번만 낸다. PreToolUse 는 **편집마다 돌기** 때문에 이것 없이
    전문을 물리면 같은 규칙이 편집 횟수만큼 쌓인다. 규칙 둘이 3KB 남짓이니
    50번 고치면 150KB 다 — 정작 지침이 뒤로 밀린다.
    표식은 세션 id 로 가른다. id 를 못 읽으면 **주입하는 쪽으로** 실패한다.
  #>
  [switch] $OncePerSession
)

$ErrorActionPreference = 'Continue'

. (Join-Path $PSScriptRoot 'lib\hook-common.ps1')

# 표준입력은 한 번만 읽을 수 있다. 쓸 데가 있으면 여기서 통째로 받아 둔다.
$payload = ''
if ($OnlyIfInputMatches -ne '' -or $OncePerSession) {
  try { $payload = [Console]::In.ReadToEnd() } catch { $payload = '' }
}

# 조건부 주입 — 이 정규식이 페이로드에 없으면 아무 일도 하지 않는다
if ($OnlyIfInputMatches -ne '' -and $payload -notmatch $OnlyIfInputMatches) { exit 0 }

$harness = Get-VreinsHarnessRoot

# 세션 표식 자리. 세션 id 를 못 읽으면 $null 이고, 그러면 매번 낸다(안전한 쪽).
$stampDir = $null
if ($OncePerSession) {
  try {
    $sid = ($payload | ConvertFrom-Json).session_id
    if ($sid) {
      $sid = ($sid -replace '[^0-9A-Za-z\-]', '')
      if ($sid) {
        $stampDir = Join-Path $env:TEMP ('vreins-hooks\' + $sid)
        if (-not (Test-Path $stampDir)) { [void](New-Item -ItemType Directory -Path $stampDir -Force) }
      }
    }
  } catch { $stampDir = $null }
}

$blocks = New-Object System.Collections.ArrayList
foreach ($name in ($Files | ForEach-Object { $_.Split(',') } | Where-Object { $_.Trim() -ne '' })) {
  $leaf = $name.Trim()
  if (-not $leaf.EndsWith(".md")) { $leaf = "$leaf.md" }

  # 이 세션에서 이미 낸 규칙은 건너뛴다
  $stamp = $null
  if ($stampDir) {
    $stamp = Join-Path $stampDir ($leaf + '.done')
    if (Test-Path $stamp) { continue }
  }

  $block = Get-VreinsDocBlock -Path (Join-Path $harness ('hooks\rules\' + $leaf)) -Label ('hooks\rules\' + $leaf)
  if ($block) {
    [void]$blocks.Add($block)
    # 실제로 낸 것만 표식을 남긴다. 파일이 없어 건너뛴 것은 다음에 다시 본다.
    if ($stamp) { try { [void](New-Item -ItemType File -Path $stamp -Force) } catch { } }
  }
}

# 낼 것이 없으면 아무것도 내지 않는다. 사유가 빈 ask 를 띄우면 사용자는 왜 묻는지
# 모른 채 승인을 누르게 된다 — 없는 것보다 나쁘다.
if ($blocks.Count -eq 0) { exit 0 }

$text = (($blocks -join [Environment]::NewLine)).TrimEnd()

<#
  실측(PS 5.1) — ConvertTo-Json 은 한글을 그대로 내고 < > ' 만 \uXXXX 로 바꾼다.
  둘 다 유효한 JSON 이고 읽는 쪽에서 원래 글자로 돌아온다.
  바이트 인코딩은 hook-common.ps1 이 [Console]::OutputEncoding 을 BOM 없는 UTF-8 로
  맞춰 둔 것에 기댄다 — 그것이 빠지면 PS 5.1 이 코드페이지 949 로 써서 깨진다.
#>
if ($AsAdditionalContext) {
  $out = [pscustomobject]@{
    hookSpecificOutput = [pscustomobject]@{
      hookEventName     = 'PreToolUse'
      additionalContext = $text
    }
  }
  Write-Output ($out | ConvertTo-Json -Depth 5 -Compress)
}
elseif ($AsPermissionAsk) {
  $out = [pscustomobject]@{
    hookSpecificOutput = [pscustomobject]@{
      hookEventName            = 'PreToolUse'
      permissionDecision       = 'ask'
      permissionDecisionReason = $text
    }
  }
  Write-Output ($out | ConvertTo-Json -Depth 5 -Compress)
}
else {
  Write-Output $text
}

exit 0
