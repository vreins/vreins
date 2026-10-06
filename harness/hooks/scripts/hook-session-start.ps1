<#
  hook-session-start.ps1  —  SessionStart 훅

  vreins-rules 스킬 1절의 「항상 읽는다」를 실제로 이행하는 자리다.
  문서가 「항상 읽어라」라고 적어 두는 것만으로는 아무것도 읽히지 않는다.
  그 문장을 읽으려면 이미 그 파일을 읽고 있어야 하므로, 부트스트랩이 따로 있어야 한다.
  플러그인은 CLAUDE.md 를 심을 수 없으므로 SessionStart 훅이 그 유일한 자리다.

  내는 것
    1  vreins-rules 를 부르라는 지시   — 전문이 아니라 한 블록. 아래 참조
    2  이 세션의 시스템   — 런처가 확정한 것
    3  {루트}\systems\{유형}\{코드}.json   항상 (시스템명 · 기술기반 · 소스 경로)
    4  {위키}\glossary.md                 항상 (용어 색인만)
    5  {위키}\{유형}\{코드}\{코드}-OVERVIEW.md   항상 (related 줄만)
    6  always-on 규칙   — 시점을 가리지 않는 것만. 지금은 handling-unknowns 하나다

  1 은 2026-10-06 까지 SKILL.md **전문**이었다. 그래서 이 출력이 12,612자가 됐고,
  클라이언트가 그것을 잘라 앞 2KB 만 모델에 주고 나머지는 파일로 뺐다. 전문 하나가
  9,913자, 곧 79% 였다. 잘린 뒤쪽에 「위키에 이 시스템의 자리가 없다」가 있었고
  그 세션은 끝까지 그것을 못 봤다 — 4.4.4 에서 더한 경고가 더하자마자 묻혀 있었다.

  전문을 넣어야 부트스트랩이 된다고 적어 두었는데, 필요한 것은 전문이 아니라
  **「불러라」한 줄**이었다. 전문은 Skill 툴이라는 안 잘리는 통로가 따로 있다.
  훅이 그 일을 중복으로 지는 동안, 훅만 낼 수 있는 나머지 21% 가 밀려났다.

  토큰은 안 줄어든다. 줄이는 것이 목적이 아니라 **잘리는 통로에서 빼는 것**이 목적이다.

  3·4 와 기술기반은 **플러그인 안이 아니다.** 2026-09-22 회의로 시스템 정보를
  플러그인에서 내렸다 — 어디서 찾는지는 hook-common.ps1 의
  Get-VreinsSystemFiles · Get-VreinsTechbaseRoot 가 정한다.

  3 은 한때 레지스트리(systems.md)의 「이 시스템 행」이었다. 그 파일은 끝내 어디에도
  만들어지지 않았고, 행이 주던 것은 시스템 정의 JSON 에 다 있었다. 그래서 정의를 직접 낸다.

  내지 않는 것
    {기술기반}-reference-*.md     명시 호출만
    단계별 기술기반 4종            단계가 정해진 뒤에 스킬이 부른다

  실패해도 항상 exit 0. 훅이 세션을 막아서는 안 된다.

  주의 — 이 파일은 반드시 UTF-8 BOM 으로 저장한다 (hook-common.ps1 머리말 참조).
#>
$ErrorActionPreference = 'Continue'

. (Join-Path $PSScriptRoot 'lib\hook-common.ps1')

$harness  = Get-VreinsHarnessRoot
$wiki     = Get-VreinsWikiRoot
$system  = Get-VreinsSystem
$techbase = Get-VreinsTechbaseRoot -SystemType $(if ($system) { $system.SystemType } else { $null })

Write-Output '===== vReins 하네스 ====='
Write-Output ''
<#
  잘림 안전장치. 전문을 뺐으니 지금은 3KB 아래지만, 출력은 또 자란다.
  자랐을 때 **조용히** 뒤가 사라지는 것이 문제였으므로 한 줄을 미리 박아 둔다.
#>
Write-Output '이 출력이 잘렸다고 표시되면(Output too large) 저장된 전문 파일을 끝까지 읽는다.'
Write-Output '앞부분만 보고 넘어가지 않는다 — 「없다」는 경고는 뒤쪽에 들어온다.'
Write-Output ''

# --- 0. 헌법을 부르게 한다 ------------------------------------------------------
<#
  전문을 싣지 않는 이유는 머리말에 적었다. 여기서는 **부르게 만드는 것**만 한다.

  첫 블록에 두는 이유 — 로딩 순서를 정하는 문서라 이것을 모르면 아래 것들이
  어떤 순서로 적용되는지 알 수 없다. 뒤에 두면 아래를 먼저 읽고 순서를 지어낸다.
#>
Write-Output '===== 먼저 할 것 ====='
Write-Output ''
Write-Output '  Skill 툴로  vreins-harness:vreins-rules  를 지금 부른다.'
Write-Output '  사용자에게 답하기 전이고, 파일을 하나라도 열기 전이다.'
Write-Output ''
Write-Output '하네스의 헌법이다 — 무엇을 언제 읽고 언제 멈추는지가 거기 있다.'
Write-Output '전문을 이 출력에 싣지 않는다. 실으면 출력이 잘려 아래 블록들이 묻힌다.'
Write-Output '실제로 묻혔다(2026-10-06). 그러니 안 부르면 하네스가 없는 것과 같다.'
Write-Output ''

# --- 1. 이 세션의 시스템 --------------------------------------------------------
<#
  어떻게 알아냈는지를 같이 낸다. 밝히지 않으면 마법처럼 보이고,
  틀렸을 때 사람이 어디를 봐야 하는지 모른다.
#>
if ($system) {
  Write-Output ('시스템       ' + $system.SystemType + ' / ' + $system.SystemCode)
  if ($system.SystemBase.Count -gt 0) { Write-Output ('기술기반   ' + ($system.SystemBase -join ', ')) }
  if ($system.Scm) { Write-Output ('형상관리   ' + $system.Scm) }
  if ($system.Source -eq 'cwd') {
    Write-Output ('확정 근거   지금 폴더가 시스템 정의의 「' + $system.MatchedKey + '」 경로 안에 있다')
    Write-Output ('           ' + $system.MatchedAt)
    Write-Output '           런처를 안 거쳤다. 틀렸으면 vReins.exe 로 다시 들어오면 된다.'
  }
} else {
  Write-Output '시스템       (미확정)'
}

<#
  둘 다 **플러그인 밖**이라 어디로 잡혔는지 밝힌다.
  2026-09-22 전에는 기술기반이 플러그인 안에 있어 밝힐 것이 없었다.
  이제는 사람마다 다른 자리에 있을 수 있고, 틀렸을 때 어디를 볼지 알아야 한다.
#>
if ($wiki)     { Write-Output ('wiki         ' + $wiki) }     else { Write-Output 'wiki         (못 찾음)' }
if ($techbase) { Write-Output ('기술기반경로 ' + $techbase) } else { Write-Output '기술기반경로 (못 찾음)' }
Write-Output ''

if (-not $system) {
  Write-Output '시스템을 확정하지 못했다. 둘 중 하나로 들어온다.'
  Write-Output '  vReins.exe 로 시스템을 골라 진입한다        ← 권장'
  Write-Output '  그 시스템의 소스 폴더에서 claude 를 띄운다   ← 시스템 정의의 경로와 대조해 알아낸다'
  Write-Output '시스템을 모르면 산출물을 어디에 쓸지 알 수 없다. 경로를 추측하지 않는다.'
  Write-Output ''
}
if (-not $wiki) {
  <#
    **사람이 고칠 자리를 알려준다.** 「못 찾았다」만 말하면 어디를 손대야 하는지
    모른다. 우리 설치기로 깐 사람과 자기 위키를 따로 세운 사람이 갈 길이 다르다.
  #>
  Write-Output '위키를 못 찾았다. 둘 중 하나를 한다.'
  Write-Output ''
  Write-Output '  1  우리 설치기를 쓴다        V-Setup.exe → C:\vReins\wiki 에 클론된다'
  Write-Output '  2  내 위키를 따로 세웠다      C:\vReins\wiki-location.txt 에 한 줄 적는다'
  Write-Output ''
  Write-Output '     # 이 아래 한 줄에 내 위키 폴더 경로를 적는다.'
  Write-Output '     # 중괄호를 지우고 실제 경로로 바꾼다 — 중괄호가 남아 있으면 안 적은 것으로 본다.'
  Write-Output '     {여기에 위키 폴더 경로를 적으세요}'
  Write-Output ''
  Write-Output '**경로를 추측해서 진행하지 않는다.** 산출물을 어디에 쓸지 모르는 채로 쓰면'
  Write-Output '엉뚱한 자리에 쌓이고, 그것을 되돌릴 방법이 없다.'
  Write-Output ''
}
if (-not $techbase) {
  if ($system) {
    Write-Output '기술기반 폴더를 못 찾았다. 셋 중 한 곳에 있어야 한다 — vreins-rules 3절.'
    Write-Output '  VREINS_TECHBASE_ROOT / {위키}\{유형}\COMMON\_manual\ / {루트}\techbase\'
  } else {
    Write-Output '기술기반 폴더는 유형마다 따로 있다 — 시스템이 정해져야 자리가 정해진다.'
  }
  Write-Output '**없으면 없는 것이다.** 다른 기술기반 지침을 가져다 쓰지 않고 그 자리에서 멈춘다.'
  Write-Output ''
}

# --- 2. 항상 읽는 지침 --------------------------------------------------------
<#
  **전문을 넣는 것이 하나도 없다.** 전부 색인이거나 그 시스템 것 하나다.

  전에는 셋 다 전문이었고 세션 시작에 16,441자가 올라갔다. 그중 절반이 용어집,
  넷 중 하나가 레지스트리였다. 둘 다 **계속 자라는 문서**라 이대로 두면
  시스템과 용어가 늘수록 정작 지침이 뒤로 밀린다. 그래서 둘을 줄였다.

  남은 전문 하나가 vreins-rules\SKILL.md 였고, 그것이 9,913자로 자라 결국
  같은 일을 했다 — 2026-10-06. 「줄일 수 없다」고 적어 두었는데 줄일 필요가
  없었다. Skill 툴로 부르면 되고, 훅은 부르라고만 하면 된다. 0절로 갔다.

    systems\{유형}\{코드}.json    이 시스템 것 하나.  세션이 쓰는 것은 자기 정의뿐이다
    wiki\glossary.md              색인.    이름만. 정의는 그 단어가 나올 때 읽는다

  $loaded 가 세는 것도 이제 이 둘과 related · OVERVIEW 부재뿐이다. 헌법은
  여기서 안 세고 못 센다 — 모델이 Skill 툴을 부르느냐에 달렸다.
#>
$loaded = 0

$block = Get-VreinsSystemDefinitionBlock -System $system
if ($block) { Write-Output $block; $loaded++ }

if ($wiki) {
  # 위키 루트의 glossary.md 다. 예전에는 wiki\_공통\guideline-Glossary.md 였고
  # 한글 폴더명이라 코드포인트로 조립했는데, 위키가 루트로 올리면서 그럴 이유가 없어졌다.
  $block = Get-VreinsGlossaryIndexBlock -Wiki $wiki
  if (-not $block) {
    # 색인을 못 뽑았다 — 위키 쪽 표 구조가 바뀌었을 수 있다.
    # 조용히 비우지 않는다. 안전한 쪽(전문)으로 되돌린다.
    $block = Get-VreinsDocBlock -Path (Join-Path $wiki 'glossary.md') -Label 'wiki\glossary.md'
  }
  if ($block) { Write-Output $block; $loaded++ }

  # 이 시스템의 related. 본문 없이 관계 줄만 — 세션 시작에 안 들어오면 아무도 안 본다.
  $block = Get-VreinsRelatedBlock -Wiki $wiki -System $system
  if ($block) { Write-Output $block; $loaded++ }

  # 위키에 자리가 아예 없는 경우. **조용히 넘어가면 아무도 안 만든다.**
  #
  # 실행기는 프로젝트를 등록해도 위키에 폴더를 만들지 않고(그쪽은 공유 저장소다),
  # lint.py 가 이것을 오류로 잡기는 하는데 부르는 훅이 없다. 그래서 등록한 사람은
  # 「등록했는데 위키에 아무것도 안 생겼다」만 보고, 왜인지는 아무 데서도 안 나온다.
  if ($system -and $system.SystemType -and $system.SystemCode) {
    $ovw = Join-Path (Join-Path (Join-Path $wiki $system.SystemType) $system.SystemCode) `
                     ($system.SystemCode + '-OVERVIEW.md')
    if (-not (Test-Path $ovw)) {
      Write-Output ('===== 위키에 이 시스템의 자리가 없다 =====')
      Write-Output ('없는 파일   wiki\' + $system.SystemType + '\' + $system.SystemCode +
                    '\' + $system.SystemCode + '-OVERVIEW.md')
      Write-Output '산출물이 갈 자리가 없다는 뜻이다. 작업을 시작하기 전에 만든다.'
      Write-Output 'wiki\_sample\ 밑의 시스템 예시({코드}-OVERVIEW.md, 절 다섯)를 베껴 고쳐 쓴다.'
      Write-Output '_sample\SAMPLE-OVERVIEW.md 는 폴더 규약 설명이라 양식이 아니다 — 그것을 베끼지 않는다.'
      Write-Output '빈 껍데기를 두지 않는다 — 절을 비워 두면 다음 사람이 누락과 구분하지 못한다.'
      $loaded++
    }
  }
}

# --- 3. always-on 규칙 --------------------------------------------------------
<#
  여기 넣는 것은 **시점을 가리지 않는 것**뿐이다. 나머지는 PreToolUse 가 그 순간에 낸다.

  갈림길은 「조언이냐 차단이냐」가 아니라 **「그 이벤트에서 모델에 닿느냐」**다.
  exit 0 의 stdout 이 모델 컨텍스트로 가는 것은 SessionStart · UserPromptSubmit 계열뿐이고,
  PreToolUse 의 stdout 은 사용자 transcript 에만 보인다. 규칙 넷을 PreToolUse · Stop 에
  stdout 으로 걸어 두었던 동안 **모델은 그 글을 한 번도 본 적이 없었다.**

  고친 길 — 이벤트마다 닿는 통로가 따로 있다.
    SessionStart   stdout                       handling-unknowns
    PreToolUse     hookSpecificOutput.additionalContext    read-before-work · no-credentials-in-docs
    PreToolUse     permissionDecision: ask      approval-before-commit
    Stop           type: prompt 의 reason       evidence-before-done

  그래서 조언 둘을 여기로 옮기지 않았다. additionalContext 는 사용자에게 묻지 않고
  모델에만 닿으므로, **그 규칙이 필요한 순간(편집 직전)에 주는 편이 낫다.**
#>
$alwaysOn = @('handling-unknowns')
foreach ($r in $alwaysOn) {
  $block = Get-VreinsDocBlock -Path (Join-Path $harness ('hooks\rules\' + $r + '.md')) -Label ('hooks\rules\' + $r + '.md')
  if ($block) { Write-Output $block }
}

# --- 4. 무엇이 아직 없는지 한 번만 알린다 --------------------------------------
# 조건부 훅은 편집마다 도니까 거기서는 아무 말도 하지 않는다. 요약은 여기 한 곳뿐이다.
$rs = Get-VreinsRuleState
$declared = 5   # 도면이 적어 둔 수 (10차에 아홉에서 넷, 12차에 게이트를 더해 다섯)
if ($rs.Ready.Count -lt $declared) {
  Write-Output '===== 아직 없는 규칙 ====='
  Write-Output ''
  Write-Output ('hooks\rules   ' + $rs.Ready.Count + ' / ' + $declared + ' 사용 가능')
  if ($rs.Ready.Count -gt 0)    { Write-Output ('  사용 가능  ' + ($rs.Ready -join ', ')) }
  if ($rs.NotReady.Count -gt 0) { Write-Output ('  미작성     ' + ($rs.NotReady -join ', ')) }
  Write-Output '  나머지는 파일이 없다. 없는 규칙은 강제되지 않는다 — 있다고 가정하지 않는다.'
  Write-Output ''
}

# --- 5. 다음 행동 -------------------------------------------------------------
Write-Output '===== 이 세션에서 지킬 것 ====='
Write-Output ''
Write-Output '  - 위 지침 중 「필수」를 위반해야 요구를 만족한다면 중단하고 보고한다.'
Write-Output '  - 지침에 없는 것을 추측해 채우지 않는다. 사용자에게 확인한다.'
Write-Output '  - 작업을 시작하기 전에 세션이 있는지 본다 → vreins-workflow 스킬'
Write-Output '  - 단계별 기술기반 지침은 영향범위가 정해진 뒤에 읽는다.'
Write-Output ''
if ($loaded -eq 0) {
  Write-Output '경고: 항상 읽어야 할 지침을 하나도 못 읽었다. 하네스가 설치되지 않은 것처럼 동작한다.'
  Write-Output ''
}

exit 0
