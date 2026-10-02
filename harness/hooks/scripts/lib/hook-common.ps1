<#
  hook-common.ps1
  훅 스크립트가 공유하는 경로 해석. dot-source 해서 쓴다.

  **이 파일은 훅이 아니다.** hooks.json 이 부르지 않고 다른 훅이 불러다 쓴다.
  그래서 lib\ 로 내렸다 — scripts\ 에 훅과 나란히 두면 훅이 늘어날수록
  「어느 것이 실제로 도는 훅인가」를 이름만 보고 못 가린다.

    scripts\hook-*.ps1     hooks.json 이 부른다 = 진짜 훅
    scripts\lib\*.ps1      훅이 불러다 쓴다 = 공용

  설정이 들어오는 길은 하나다 — **런처가 넣은 환경변수.**
  vReins.exe 가 시스템을 확정하고 VREINS_* 를 채운 뒤 claude 를 띄운다.
  런처 없이 claude 를 직접 띄우면 이 값들이 비고, 하네스는 「모른다」고 보고한다.
  추측해서 경로를 만들지 않는다.

  주의 — 이 파일은 반드시 UTF-8 BOM 으로 저장한다.
  Windows PowerShell 5.1 은 BOM 이 없으면 .ps1 을 ANSI 로 읽어 한글 리터럴이 깨진다.
  판정에 쓰는 문자열은 코드포인트로 조립해 저장 인코딩과 무관하게 만든다.
#>

<#
  표준출력을 UTF-8 로 고정한다. 이것이 빠지면 주입된 한글이 전부 깨진다.

  Claude Code 는 훅을 `powershell -NoProfile -File ...` 로 띄우고 stdout 을 읽는다.
  그 프로세스는 콘솔 설정을 물려받지 않으므로 PowerShell 5.1 이 OEM 코드페이지(949)로
  쓰고, Claude 는 그것을 UTF-8 로 읽어 모지바케가 된다.

  파일에 BOM 이 있어도 소용없다 — BOM 은 「읽기」를 고치고 이것은 「쓰기」다.
  둘 다 필요하다.

  이 파일을 dot-source 하는 모든 훅이 여기서 한 번에 고쳐진다.
#>
try {
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [Console]::OutputEncoding = $utf8NoBom
  $OutputEncoding = $utf8NoBom
} catch { }

# 플러그인 루트 — 훅에서는 ${CLAUDE_PLUGIN_ROOT} 가 잡히고, 직접 실행하면 위치로 역산한다
function Get-VreinsHarnessRoot {
  if ($env:CLAUDE_PLUGIN_ROOT -and (Test-Path $env:CLAUDE_PLUGIN_ROOT)) { return $env:CLAUDE_PLUGIN_ROOT }
  # $PSScriptRoot 는 이 파일이 있는 scripts\lib 다. 루트까지 세 단계 올라간다.
  #   lib -> scripts -> hooks -> harness.  한 번 모자라면 harness\hooks 가 나오고
  #   규칙을 하나도 못 읽는다 — 실제로 그랬다(2026-09-21).
  return (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)))
}

<#
  내 루트. 런처가 안 넣어 줬으면 팀 약속값을 쓴다.
  VREINS_ROOT 로 덮을 수 있다 — 시험용이고 화면에는 없다.
#>
function Get-VreinsRoot {
  if ($env:VREINS_ROOT -and (Test-Path $env:VREINS_ROOT)) { return $env:VREINS_ROOT }
  if (Test-Path 'C:\vReins') { return 'C:\vReins' }
  return $null
}

<#
  **사람이 손으로 적는 자리.** `{루트}\wiki-location.txt` 한 줄이다.

  플러그인 안에 적게 하지 않는 이유 — 거기는 갱신 때 통째로 덮인다.
  적어 둔 것이 조용히 사라지고, 왜 사라졌는지 알 방법이 없다.

  형식은 일부러 단순하다. `#` 로 시작하는 줄과 빈 줄을 건너뛰고
  **처음 나오는 줄**을 경로로 본다. 중괄호로 감싼 자리표시자
  (`{여기에 적으세요}` 같은 것)는 **아직 안 적은 것**으로 보고 건너뛴다 —
  받자마자 그대로 두면 그 값이 경로로 읽히는 일을 막는다.
#>
function Get-VreinsWikiFromFile {
  $root = Get-VreinsRoot
  if (-not $root) { return $null }
  $f = Join-Path $root 'wiki-location.txt'
  if (-not (Test-Path $f)) { return $null }
  foreach ($line in (Get-Content $f -Encoding utf8 -ErrorAction SilentlyContinue)) {
    $v = $line.Trim()
    if (-not $v) { continue }
    if ($v.StartsWith('#')) { continue }
    # 자리표시자를 값으로 읽지 않는다 — {…} · (…) · <…> 는 「아직 안 적음」이다
    if ($v -match '^[\{\(\<].*[\}\)\>]$') { continue }
    if (Test-Path $v) { return $v }
    return $null   # 적혀는 있는데 그런 폴더가 없다 → 추측하지 않고 없다고 본다
  }
  return $null
}

<#
  산출물이 쌓이는 곳. 넷을 차례로 본다.

    VREINS_WIKI_ROOT           런처가 넣는다
    {루트}\wiki-location.txt   **사람이 적는 자리.** 본인 위키를 따로 두었을 때
    {루트}\wiki\               설치기가 클론한 기본 자리
                               못 찾으면 $null — 경로를 지어내지 않는다
#>
function Get-VreinsWikiRoot {
  if ($env:VREINS_WIKI_ROOT -and (Test-Path $env:VREINS_WIKI_ROOT)) { return $env:VREINS_WIKI_ROOT }
  $fromFile = Get-VreinsWikiFromFile
  if ($fromFile) { return $fromFile }
  $root = Get-VreinsRoot
  if ($root) {
    $w = Join-Path $root 'wiki'
    if (Test-Path $w) { return $w }
  }
  return $null
}

<#
  기술기반 지침이 있는 곳. **플러그인이 아니다.**

  2026-09-22 회의로 시스템·기술기반 정보는 플러그인에서 내렸다. 플러그인은
  우리 조직이 아닌 사람이 받아 써도 되는 범용 뼈대만 담고, 「무엇을 지킬 것인가」는
  각자의 위키가 갖는다. 그래서 여기를 **찾는** 것이지 **아는** 것이 아니다.

    VREINS_TECHBASE_ROOT              런처·시험용. 있으면 무조건 이긴다
    {위키}\{유형}\COMMON\_manual\    정본. 지침과 받은 문서가 한 폴더에 있고 머리말 `강도` 로 가른다
    {루트}\techbase\                  위키를 따로 두지 않는 사람

  2026-09-28 위키가 `COMMON\techbase\` 를 `COMMON\_manual\` 로 합쳤다 — 「누가 썼나」로
  폴더를 가르지 않고 「꼭 읽나」로 가른다. 지침은 파일 이름이 `{기술기반}-{이름}.md` 라
  같은 폴더에 받은 문서가 섞여 있어도 가려진다. 옛 자리 `COMMON\techbase\` 는 더 보지 않는다 —
  한 번 옮긴 자리를 계속 보면 둘 다 있을 때 어느 쪽을 읽었는지 모른다.

  **못 찾으면 $null 이다.** 다른 폴더를 가져다 쓰지 않는다 — 없다는 사실이
  그대로 보여야 한다(handling-unknowns).
#>
function Get-VreinsTechbaseRoot {
  param([string] $SystemType)
  if ($env:VREINS_TECHBASE_ROOT -and (Test-Path $env:VREINS_TECHBASE_ROOT)) { return $env:VREINS_TECHBASE_ROOT }
  $wiki = Get-VreinsWikiRoot
  if ($wiki -and $SystemType) {
    # 유형마다 따로 있다 — 시스템을 모르면 이 자리는 정할 수 없다
    $t = Join-Path (Join-Path (Join-Path $wiki $SystemType) 'COMMON') '_manual'
    if (Test-Path $t) { return $t }
  }
  $root = Get-VreinsRoot
  if ($root) {
    $t = Join-Path $root 'techbase'
    if (Test-Path $t) { return $t }
  }
  return $null
}

<#
  시스템 정의를 전부 읽는다. **한 층이다.**

    {루트}\systems\{유형}\{코드}.json      내 PC 에 등록된 것

  한때 플러그인\systems\ 를 「팀 공통」 층으로 같이 봤다. 2026-09-22 회의로 시스템 정보는
  플러그인에 넣지 않기로 했으므로 그 층은 언제나 비어 있었다 — 비어 있는 층을 계속 보면
  문서가 「두 층」이라고 거짓말을 한다. 레지스트리(systems.md)도 같은 날 없앴다 —
  시스템명·기술기반·형상관리는 이 파일이, 설명·소유자·관계는 그 시스템 문서 머리말이 갖는다.
  같은 것을 세 벌 적으면 둘은 반드시 낡는다.
#>
function Get-VreinsSystemFiles {
  $out = New-Object System.Collections.ArrayList
  $root = Get-VreinsRoot
  if (-not $root) { return $out }
  $d = Join-Path $root 'systems'
  if (-not (Test-Path $d)) { return $out }
  foreach ($f in (Get-ChildItem $d -Recurse -Filter *.json -File -ErrorAction SilentlyContinue)) {
    if ($f.Name -like '*.local.json') { continue }            # 옛 계정 파일. 시스템이 아니다
    $type = $f.Directory.Name
    $code = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
    try { $j = Get-Content $f.FullName -Raw -Encoding utf8 | ConvertFrom-Json } catch { continue }
    [void]$out.Add([pscustomobject]@{ Type = $type; Code = $code; Json = $j; Path = $f.FullName })
  }
  return $out
}

<#
  이 세션의 시스템.

  **길이 둘이다.** 런처로 들어오면 환경변수에 이미 있고, 직접 들어오면
  **지금 폴더로 역추적**한다.

  역추적은 추측이 아니다 — 시스템 정의의 「경로」 값과 현재 폴더를 대조한다.
  그 값은 커밋된 정본이고 모두에게 같다. 이름으로 폴더를 맞히려던 옛 방식(2차에
  버렸다)과 다른 점이 그것이다. **맞히는 것이 아니라 적혀 있는 것과 비교한다.**

  **logs 만 뺀다.** 로그 공유폴더는 담당이 아니어도 열리므로 「내 시스템」 판정에
  쓰면 안 된다 (7차가 메뉴를 거를 때 쓴 기준과 같다). 나머지 — frontend · backend ·
  repo · 기술기반 이름 — 는 전부 진짜 소스 자리라 본다.

  한때 systemBase 키만 봤는데 틀렸다. 경로 키를 역할 이름(프론트엔드·백엔드)으로
  붙일 수 있게 하면서, 키가 기술기반 이름이 아닌 시스템은 영영 못 찾게 됐다.
  **키 이름이 아니라 「로그인가 아닌가」로 가른다.**

  겹치면 **더 긴 경로가 이긴다.** 상위 폴더를 가진 시스템이 하위를 가로채지 않는다 —
  repo 에 솔루션 최상위를 적어 둔 시스템이 그 안의 다른 시스템을 삼키는 것을 막는다.
#>
function Get-VreinsSystem {
  if ($env:VREINS_SYSTEM_CODE) {
    # 런처가 준 값이 정답이다. 정의 파일은 경로를 알려 주려고 **찾아만** 둔다 — 없어도 확정은 된다.
    $def = $null
    foreach ($f in (Get-VreinsSystemFiles)) {
      if ($f.Type -eq $env:VREINS_SYSTEM_TYPE -and $f.Code -eq $env:VREINS_SYSTEM_CODE) { $def = $f; break }
    }
    return [pscustomobject]@{
      SystemType = $env:VREINS_SYSTEM_TYPE
      SystemCode = $env:VREINS_SYSTEM_CODE
      SystemBase = @($env:VREINS_SYSTEM_BASE -split '[,;]' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
      Scm        = $env:VREINS_SCM
      Source     = 'launcher'
      MatchedAt  = $null
      MatchedKey = $null
      Definition = $def
    }
  }

  $cwd = ''
  try { $cwd = (Get-Location).Path.TrimEnd('\') } catch { return $null }
  if (-not $cwd) { return $null }

  $best = $null; $bestLen = -1
  foreach ($f in (Get-VreinsSystemFiles)) {
    $paths = $f.Json.'경로'
    if (-not $paths) { continue }
    foreach ($prop in $paths.PSObject.Properties) {
      if ($prop.Name -eq 'logs') { continue }
      $p = $prop.Value
      if (-not $p) { continue }
      $p = ([string]$p).TrimEnd('\')
      if ($p.Length -le $bestLen) { continue }
      if ($cwd -eq $p -or $cwd.StartsWith($p + '\', [StringComparison]::OrdinalIgnoreCase)) {
        $bestLen = $p.Length
        $best = [pscustomobject]@{
          SystemType = $f.Type
          SystemCode = $f.Code
          SystemBase = @(@($f.Json.systemBase) | Where-Object { $_ })
          Scm        = [string]$f.Json.'형상관리'
          Source     = 'cwd'
          MatchedAt  = $p
          MatchedKey = $prop.Name
          Definition = $f
        }
      }
    }
  }
  return $best
}

# '상태: 미작성' 판정 — 인코딩 무관하게 코드포인트로 조립한다
function Get-VreinsUnwrittenPattern {
  $kStatus    = [string]::Join('', [char]0xC0C1, [char]0xD0DC)               # 상태
  $kUnwritten = [string]::Join('', [char]0xBBF8, [char]0xC791, [char]0xC131) # 미작성
  return ('(?m)^>\s*' + $kStatus + ':\s*' + $kUnwritten + '\s*$')
}

<#
  주입할 블록을 만들어 돌려준다. 규칙은 셋뿐이다.
    없는 파일        건너뛴다. 다른 파일로 대체하지 않는다
    상태: 미작성     읽지 않은 것으로 취급한다 (vreins-rules 스킬 2절)
    그 밖           전문을 그대로 낸다. 요약하지 않는다

  건너뛸 때 아무것도 내지 않는다 — 조건부 훅은 편집마다 돌기 때문에
  「없어서 건너뜀」을 매번 찍으면 그것만으로 컨텍스트가 오염된다.
  세션 시작에 hook-session-start.ps1 이 한 번만 요약해서 알린다.

  반환값: 블록 문자열, 건너뛰면 $null

  주의 — 본문을 함수 안에서 Write-Output 하면 안 된다.
  PowerShell 은 함수가 출력 스트림에 쓴 것을 전부 반환값으로 본다.
  그러면 if (…) 조건이나 | Out-Null 에 본문까지 함께 먹혀 아무것도 주입되지 않는다.
#>
function Get-VreinsDocBlock {
  param(
    [Parameter(Mandatory = $true)][string] $Path,
    [Parameter(Mandatory = $true)][string] $Label
  )

  if (-not (Test-Path $Path)) { return $null }

  $text = Get-Content -Path $Path -Raw -Encoding utf8
  if ($text -match (Get-VreinsUnwrittenPattern)) { return $null }

  return ("===== " + $Label + " =====" + [Environment]::NewLine + $text.TrimEnd() + [Environment]::NewLine)
}

<#
  마크다운 표에서 각 행의 첫 칸을 뽑는다. 머리 행과 구분선은 뺀다.

  **한글 리터럴로 머리 행을 거르지 않는다.** 「용어」·「코드」 같은 말을 적어 두면
  이 파일의 저장 인코딩에 판정이 묶이고, 위키 쪽에서 컬럼 이름을 바꾸면 조용히 깨진다.
  대신 **자리로 가른다** — 마크다운에서 머리 행은 「다음 줄이 구분선인 줄」이다.
  언어와 무관하고, 표 모양이 유지되는 한 안 깨진다.
#>
function Get-VreinsTableFirstCells {
  param(
    # AllowEmptyString 이 있어야 한다. Mandatory 인 [string[]] 는 **빈 문자열 원소를 거부**하고,
    # 문서에는 빈 줄이 반드시 있다. 없으면 바인딩 단계에서 통째로 실패한다.
    [AllowEmptyString()]
    [string[]] $Lines = @(),
    [int] $From = 0,
    [int] $To = -1
  )
  if ($Lines.Count -eq 0) { return (New-Object System.Collections.ArrayList) }
  if ($To -lt 0 -or $To -ge $Lines.Count) { $To = $Lines.Count - 1 }
  $out = New-Object System.Collections.ArrayList
  for ($i = $From; $i -le $To; $i++) {
    $l = $Lines[$i]
    if ($l -notmatch '^\s*\|') { continue }
    if ($l -match '^\s*\|[\s:\-|]+\|\s*$') { continue }                                   # 구분선
    if ($i + 1 -le $To -and $Lines[$i + 1] -match '^\s*\|[\s:\-|]+\|\s*$') { continue }   # 머리 행
    if ($l -match '^\s*\|\s*([^|]+?)\s*\|') {
      $t = $Matches[1].Trim()
      if ($t -and -not $out.Contains($t)) { [void]$out.Add($t) }
    }
  }
  return $out
}

<#
  이 세션의 **시스템 정의**를 짧게 낸다 — 시스템명 · 기술기반 · 형상관리 · 소스 경로.

  한때 여기서 레지스트리(systems.md)의 「이 시스템 행」을 뽑았다. 그 행이 주던 것은
  전부 시스템 정의 JSON 에 이미 있었고, 레지스트리 파일은 끝내 어디에도 만들어지지 않아
  세션마다 「못 찾았다」만 찍혔다. 그래서 정의 파일을 직접 낸다.

  **경로를 내는 것이 핵심이다.** 런처로 들어오면 환경변수에는 유형·코드·기술기반만 있고
  소스가 어디 있는지는 없다. 그러면 모델이 경로를 추측하게 된다 — 그 자리를 막는다.

  `db` 는 값을 싣지 않는다. 호스트가 들어 있고, 세션 로그에 남길 이유가 없다.
  있다는 사실만 낸다. 계정은 애초에 이 파일에 없다 — {루트}\config\ 에만 있다.

  확정된 시스템을 인자로 받는다. **환경변수를 직접 보지 않는다** — 시스템을 정하는
  자리는 Get-VreinsSystem 하나뿐이어야 한다. 시스템이 없으면 $null — 그 사실은
  세션 시작 훅 1절이 이미 말했다. 정의 파일만 없으면 그 사실을 낸다.
#>
function Get-VreinsSystemDefinitionBlock {
  param($System)

  if (-not $System -or -not $System.SystemCode) { return $null }
  $nl = [Environment]::NewLine
  $label = 'systems\' + $System.SystemType + '\' + $System.SystemCode + '.json'

  $def = $System.Definition
  if (-not $def) {
    return ('===== ' + $label + ' — 시스템 정의 =====' + $nl +
            '이 PC 에 정의 파일이 없다. 런처가 준 유형·코드·기술기반만 안다 — **소스 경로는 모른다.**' + $nl +
            '경로를 추측하지 않는다. 사용자에게 묻거나, 런처 [프로젝트 추가] 에서 등록하게 한다.' + $nl)
  }

  $j  = $def.Json
  $sb = New-Object System.Text.StringBuilder
  [void]$sb.Append('===== ' + $label + ' — 시스템 정의 =====').Append($nl)
  if ($j.'시스템명') { [void]$sb.Append('시스템명     ' + $j.'시스템명').Append($nl) }
  $base = @(@($j.systemBase) | Where-Object { $_ })
  [void]$sb.Append('기술기반     ' + $(if ($base.Count -gt 0) { $base -join ', ' } else { '(없음 — 읽을 지침이 없다는 뜻이고 그게 맞는 값이다)' })).Append($nl)
  if ($j.'형상관리') { [void]$sb.Append('형상관리     ' + $j.'형상관리').Append($nl) }
  $paths = $j.'경로'
  if ($paths) {
    [void]$sb.Append('경로').Append($nl)
    foreach ($prop in $paths.PSObject.Properties) {
      if (-not $prop.Value) { continue }
      [void]$sb.Append('  ' + $prop.Name.PadRight(12) + ' ' + $prop.Value).Append($nl)
    }
  }
  if ($j.db) { [void]$sb.Append('db           있다. 값은 여기 안 싣는다 — 계정은 {루트}\config\ 에만 있다').Append($nl) }
  [void]$sb.Append($nl)
  [void]$sb.Append('소스는 위 경로에 있다. 다른 폴더를 소스로 짐작하지 않는다. `logs` 는 소스가 아니다.').Append($nl)
  return $sb.ToString()
}

<#
  용어집을 **색인으로** 줄인다. 이름만 싣고 정의는 싣지 않는다.

  왜 「모를 때만 찾아보게」로 두지 않나 — **모른다는 것을 모르기 때문이다.**
  「정정」·「장입」·「편성」은 평범한 한국어처럼 생겼다. 실패는 「이 단어를 모르겠다」가
  아니라 일상적 뜻으로 확신을 갖고 읽어 버리는 것이고, 그러면 찾아볼 생각이 안 든다.
  **목록이 곧 방아쇠다** — 이름이 거기 있으면 정의된 용어라는 것을 알게 된다.

  뽑지 못하면 $null 을 돌려준다. 부르는 쪽이 전문 주입으로 되돌린다 —
  **안전한 쪽으로 실패시킨다.**

  색인 파일을 따로 두지 않는 이유는 늘 같다. 두 벌이면 한쪽이 낡는다.
#>
function Get-VreinsGlossaryIndexBlock {
  param([Parameter(Mandatory = $true)][string] $Wiki)

  $path = Join-Path $Wiki 'glossary.md'
  if (-not (Test-Path $path)) { return $null }
  $text = Get-Content $path -Raw -Encoding utf8
  if ($text -match (Get-VreinsUnwrittenPattern)) { return $null }

  $lines = $text -split "`r?`n"
  $nl = [Environment]::NewLine

  # 절 단위로 모은다. 묶여 있으면 사람도 LLM 도 훑기 쉽다
  $marks = @()
  for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match '^##\s+(.+?)\s*$') { $marks += [pscustomobject]@{ At = $i; Name = $Matches[1] } } }
  if ($marks.Count -eq 0) { return $null }

  $parts = @(); $total = 0
  for ($k = 0; $k -lt $marks.Count; $k++) {
    $from = $marks[$k].At + 1
    $to   = if ($k + 1 -lt $marks.Count) { $marks[$k + 1].At - 1 } else { $lines.Count - 1 }
    $cells = Get-VreinsTableFirstCells -Lines $lines -From $from -To $to
    if ($cells.Count -eq 0) { continue }
    $total += $cells.Count
    $parts += ('  ' + $marks[$k].Name + '   ' + (($cells) -join ' · '))
  }
  if ($total -eq 0) { return $null }

  $sb = New-Object System.Text.StringBuilder
  [void]$sb.Append('===== wiki\glossary.md — 용어 색인 (' + $total + '개. 정의는 싣지 않았다) =====').Append($nl)
  foreach ($p in $parts) { [void]$sb.Append($p).Append($nl) }
  [void]$sb.Append($nl)
  [void]$sb.Append('이 목록에 있는 말이 나오면 뜻을 추측하지 않는다. wiki\glossary.md 에서 그 항목을 읽는다.').Append($nl)
  [void]$sb.Append('평범한 한국어처럼 보여도 여기 있으면 현장 용어다 — 일상적 뜻으로 읽으면 틀린다.').Append($nl)
  return $sb.ToString()
}

# hooks\rules\ 에서 실제로 주입 가능한 것과 아닌 것을 센다. 세션 시작 요약용.
function Get-VreinsRuleState {
  $dir = Join-Path (Get-VreinsHarnessRoot) 'hooks\rules'
  $ready = @(); $notReady = @()
  if (Test-Path $dir) {
    foreach ($f in (Get-ChildItem $dir -Filter *.md -File)) {
      $t = Get-Content $f.FullName -Raw -Encoding utf8
      if ($t -match (Get-VreinsUnwrittenPattern)) { $notReady += $f.BaseName } else { $ready += $f.BaseName }
    }
  }
  return [pscustomobject]@{ Ready = $ready; NotReady = $notReady }
}

<#
  그 시스템 문서({시스템코드}-OVERVIEW.md)의 `related:` 만 뽑는다. 본문은 안 싣는다.

  **관계는 세션 시작에 들어와야 한다.** 파일을 열어야 보이면 이미 늦다 —
  MES 화면을 고치면서 LEVEL2 전문이 밀리는 건이 실측 77%였는데,
  그때 LEVEL2 쪽 overview 를 열어 볼 이유가 그 사람에게는 없다.

  형식은 문자열 한 줄이다 — `상대 | 태그들 | 무엇으로·왜 | 확인`.
  맵이 아니라 문자열인 이유는 **옵시디언 속성 편집기가 맵을 못 고치기 때문**이다.
  고치다 깨지는 형식은 안 고쳐진다.
#>
function Get-VreinsRelatedBlock {
  param(
    [Parameter(Mandatory = $true)][string] $Wiki,
    $System
  )

  $type = if ($System) { $System.SystemType } else { $null }
  $code = if ($System) { $System.SystemCode } else { $null }
  if (-not $type -or -not $code) { return $null }

  $path = Join-Path (Join-Path (Join-Path $Wiki $type) $code) ($code + '-OVERVIEW.md')
  if (-not (Test-Path $path)) { return $null }

  $lines = (Get-Content $path -Raw -Encoding utf8) -split "`r?`n"
  $nl = [Environment]::NewLine

  # frontmatter 안에서만 본다. 본문에 같은 낱말이 나와도 안 걸리게.
  $end = -1
  for ($i = 1; $i -lt $lines.Count; $i++) { if ($lines[$i] -match '^---\s*$') { $end = $i; break } }
  if ($end -lt 0) { return $null }

  # 인라인(`related: ["[[A]]", "[[B]]"]`)과 블록 둘 다 받는다.
  # 값이 통째로 [[..]] 라야 옵시디언이 링크로 잡으므로 형태가 인라인으로 굳었다.
  $raw = ''
  for ($i = 1; $i -lt $end; $i++) {
    if ($lines[$i] -match '^related:\s*(.*)$') {
      $raw = $Matches[1]
      for ($k = $i + 1; $k -lt $end; $k++) {
        if ($lines[$k] -match '^\s') { $raw += ' ' + $lines[$k] } else { break }
      }
      break
    }
  }
  if (-not $raw) { return $null }

  $names = @()
  foreach ($m in [regex]::Matches($raw, '\[\[([^\]]+)\]\]')) {
    $v = $m.Groups[1].Value.Trim()
    # [[MESD-OVERVIEW|MESD]] 형태면 별칭(뒤)만 쓴다. 사람이 읽는 것은 시스템코드다.
    if ($v -match '\|') { $v = ($v -split '\|')[-1].Trim() }
    if ($v -and ($names -notcontains $v)) { $names += $v }
  }
  if ($names.Count -eq 0) { return $null }

  $sb = New-Object System.Text.StringBuilder
  [void]$sb.Append('===== wiki\' + $type + '\' + $code + '\' + $code + '-OVERVIEW.md — related (' + $names.Count + '건) =====').Append($nl)
  [void]$sb.Append('  ' + ($names -join ' · ')).Append($nl)
  [void]$sb.Append($nl)
  [void]$sb.Append('이 시스템과 엮인 시스템들이다. **어떻게 엮였는지는 여기 없다** — 그 시스템 문서 2절').Append($nl)
  [void]$sb.Append('「다른 시스템과」 표에 축·방향·접근(조회만/쓰기)과 근거가 있다.').Append($nl)
  [void]$sb.Append('위 이름이 걸리는 작업이면 **고치기 전에 그 표를 읽는다.** 특히 접근이 `쓰기` 면 내가 상대를 깨뜨릴 수 있다.').Append($nl)
  [void]$sb.Append('**02 분석과 TS 에서는 그쪽 이력도 본다** — 축이 `층구분` 이나 `공정흐름` 인 시스템만. 화면코드 체계가 달라 이름으로는 안 만난다.').Append($nl)
  [void]$sb.Append('관계를 새로 알게 되면 이 파일 머리말 related 에 이름을 더하고 2절 표에 줄을 더한다 — 둘의 목록은 같아야 한다.').Append($nl)
  [void]$sb.Append('쓸 수 있는 말은 wiki\관계.md 에 있다.').Append($nl)
  return $sb.ToString()
}

