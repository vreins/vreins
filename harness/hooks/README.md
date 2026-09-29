# 훅

훅에 관한 것은 전부 이 폴더에 있다. 이름만 보고 훅인지 알 수 있어야 한다.

    hooks.json        이벤트 → 무엇을 주입할지
    scripts\          훅이 실제로 실행하는 것. 파일명은 전부 hook- 으로 시작한다
    rules\            훅이 주입하는 문장들

## 훅의 역할

`vreins-rules` 스킬이 「항상 읽어라」라고 적어 두는 것만으로는 아무것도 읽히지 않는다.
그 문장을 읽으려면 **이미 그 파일을 읽고 있어야** 하기 때문이다.
플러그인은 `CLAUDE.md` 를 심을 수 없으므로 `SessionStart` 훅이 그 유일한 자리다.

## 어느 이벤트가 모델에 닿나 — 이것이 먼저다

**훅이 도는 것과 모델이 보는 것은 다른 얘기다.** exit 0 의 stdout 이 모델
컨텍스트로 들어가는 이벤트는 정해져 있다.

| 이벤트 | `command` 훅의 stdout |
|---|---|
| `SessionStart` · `UserPromptSubmit` 계열 | **모델 컨텍스트로 들어간다** |
| `PreToolUse` · `PostToolUse` · `Stop` | 들어가지 않는다. 사용자 transcript 에만 보인다 |

한동안 규칙 넷을 `PreToolUse` · `Stop` 에 stdout 으로 걸어 두고 「걸었다」고 여겼는데,
**모델은 한 번도 그 글을 본 적이 없었다.** 막지 못하면서 초록불을 켜는 검사가
제일 해롭다.

**stdout 이 안 닿는다고 그 이벤트를 포기할 이유는 없다.** 이벤트마다 닿는 통로가
따로 있고, 규칙의 성격에 맞는 통로를 고르면 된다.

| 규칙 | 이벤트 | 닿는 통로 | 사용자에게 묻나 |
|---|---|---|---|
| `handling-unknowns` | `SessionStart` | stdout | 아니오 |
| `read-before-work` · `no-credentials-in-docs` | `PreToolUse` (편집 계열) | `hookSpecificOutput.additionalContext` | **아니오** |
| `approval-before-commit` | `PreToolUse` (Bash) | `permissionDecision: "ask"` | 예 — 그래야 하는 규칙이다 |
| `evidence-before-done` | `Stop` | `type: "prompt"` 의 `reason` | 아니오 |

`additionalContext` 가 이 표의 핵심이다. **모델에만 조용히 닿고 승인 창을 띄우지
않는다.** 그래서 조언 성격의 규칙을 「편집 직전」이라는 제일 쓸모 있는 자리에
그대로 둘 수 있다 — 세션 시작으로 옮겨 희석시킬 필요가 없다.
`ask`/`deny` 는 반대다. 편집마다 승인 창이 뜨면 아무도 안 쓴다.

### 실측 — 문서만 보고 정하지 않았다

공식 문서는 `additionalContext` 를 주로 `UserPromptSubmit` 예제로 설명한다.
`PreToolUse` 에서도 먹는지는 **직접 돌려서 확인했다.**

    PreToolUse 에 additionalContext 를 내는 훅을 걸고 claude -p 로 툴을 쓰게 했다
      → 모델이 그 문구를 그대로 받아 적었다. 한글도 안 깨졌다
    Stop 의 type: "prompt" 훅이 ok:false 를 내게 하고 돌렸다
      → reason 이 모델에게 돌아갔고, 모델이 이어서 일했다

## 셋으로 나눈 이유

| 파일 | 언제 도나 | 무엇을 내나 |
|---|---|---|
| `hook-session-start.ps1` | 세션 시작에 한 번 | 시스템 확인 + 항상 읽는 지침 + always-on 규칙 |
| `hook-inject-rule.ps1` | 편집 직전 · 커밋 직전 | 그 순간의 규칙을 **JSON 으로** |
| `hook-common.ps1` | (실행 안 됨) | 위 둘이 dot-source 하는 경로 해석 |

`hook-inject-rule.ps1` 은 기본값으로 전문을 stdout 에 낸다. **`PreToolUse` 에 걸 때는
반드시 `-AsAdditionalContext` 나 `-AsPermissionAsk` 중 하나를 준다** — 안 주면
돌기는 돌고 아무에게도 안 닿는다.

조건부 훅은 파일이 없을 때 아무 말도 하지 않는다 — 「없어서 건너뜀」을 찍으면
그것만으로 컨텍스트가 오염되고, `ask` 라면 사유가 빈 승인 창이 뜬다.
없는 것의 요약은 `hook-session-start.ps1` 한 곳에서만 한 번 낸다.

### `-OncePerSession`

`PreToolUse` 는 **편집마다 돈다.** 규칙 전문을 그냥 물리면 같은 글이 편집 횟수만큼
쌓인다 — 규칙 둘이 3KB 남짓이니 50번 고치면 150KB 고, 그러면 정작 지침이 뒤로 밀린다.
그래서 편집 계열 훅은 세션당 한 번만 낸다. 표식은 훅 입력의 `session_id` 로 가르고
`%TEMP%reins-hooks\{세션id}\` 에 남긴다.

세션 id 를 못 읽으면 표식을 포기하고 **주입하는 쪽으로** 실패한다.
규칙이 두 번 보이는 것보다 한 번도 안 보이는 것이 나쁘다.

## `Stop` 은 스크립트를 쓰지 않는다

`Stop` 은 `command` 훅의 stdout 이 모델에 안 닿으므로 `type: "prompt"` 를 쓴다.
`hooks.json` 에 문구를 직접 적고 스크립트는 없다. 판정 모델이
`{"ok": false, "reason": ...}` 을 내면 그 `reason` 이 Claude 에게 돌아간다.

전문은 `rules\evidence-before-done.md` 에 있고, `prompt` 에는 주장→증거 표만
줄여 담고 그 파일을 가리킨다. **두 벌이 되지 않게 프롬프트를 늘리지 않는다.**

무한루프는 두 겹으로 막는다.

    Claude Code 가 연속 8번 블록하면 그 Stop 훅을 자동 해제한다
    prompt 첫 줄에 「stop_hook_active 가 true 면 ok:true」를 박았다

**공식 문서는 `type: "prompt"` 훅이 `stop_hook_active` 를 받는지 적어 두지 않았다.
그래서 돌려서 확인했다** — 훅 입력의 그 값을 그대로 뱉게 하니 첫 번째 정지에
`false`, 다시 막은 뒤에는 `true` 로 왔다. 프롬프트의 그 한 줄은 실제로 동작한다.

## 설정이 들어오는 길

**환경변수 하나뿐이다.** 런처(`vReins.exe`)가 시스템을 확정하고 채운다.

    VREINS_SYSTEM_TYPE · VREINS_SYSTEM_CODE · VREINS_SYSTEM_BASE · VREINS_SCM
    VREINS_WIKI_ROOT   · VREINS_TF_PATH

`userConfig` 를 두지 않는 이유가 이것이다 — 같은 값을 두 군데서 물으면
어느 쪽이 맞는지 알 수 없게 된다. 런처 없이 들어오면 이 값들이 비고,
하네스는 **모른다고 보고한다.** 경로를 추측하지 않는다.

## 인코딩

`.ps1` 은 **반드시 UTF-8 BOM** 으로 저장한다.
Windows PowerShell 5.1 은 BOM 이 없으면 ANSI 로 읽어 한글 리터럴이 깨진다.

그래도 저장이 잘못될 수 있으므로, **판정에 쓰는 한글 문자열은 코드포인트로 조립한다.**
`상태: 미작성` 판정이 그렇다 — 저장 인코딩과 무관하게 동작한다.

`_공통` 폴더명도 그랬는데, 위키가 용어집을 루트 `glossary.md` 로 올리면서
조립할 한글이 없어졌다. **경로에 한글이 없으면 이 장치도 필요 없다.**

## 실패 처리

모든 훅 스크립트는 실패해도 `exit 0` 한다.
지침 주입이 안 되는 것보다 세션이 안 열리는 것이 나쁘다.
