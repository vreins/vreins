# 무엇이 어디서 왔나

이 하네스는 **obra/superpowers 의 뼈대**를 가져와 가지치기하고, 그 위에
시스템 도메인(시스템 정의 · 기술기반 · 산출물 양식)을 얹은 것이다.

    원저작    Jesse Vincent
    출처      https://github.com/obra/superpowers   (v6.0.3)
    라이선스  MIT — 전문은 이 폴더의 LICENSE
    저작권    Copyright (c) 2025 Jesse Vincent

MIT 는 수정·번역·재배포를 허용하되 **저작권 고지와 라이선스 전문을 함께 둘 것**을
조건으로 한다. 번역은 파생물이므로 `LICENSE` 가 배포에 따라간다.

**파일마다 머리말에도 출처를 적는다.** 이 문서 하나만 두면 파일을 개별로
가져간 사람이 출처를 모른다.

---

## 가져온 뼈대

구조가 superpowers 의 것이다.

```
skills\{이름}\SKILL.md              한 스킬이 한 폴더
skills\{이름}\references\           본문에 안 넣고 필요할 때 읽는 것
hooks\hooks.json + scripts\         훅이 세션에 개입하는 방식
```

**세션 시작에 「항상 읽는 것」을 통째로 주입하고, 나머지는 필요할 때 부르는**
방식도 그쪽에서 왔다 (`using-superpowers` → 우리 `vreins-rules`).

## 스킬 — 파생 넷 · 우리 것 셋

**우리 스킬은 전부 `vreins-` 로 시작한다** (2026-09-22). 상류와 이름이 같으면
한 세션에 두 플러그인이 깔렸을 때 어느 쪽인지 알 수 없다 —
`writing-plans` · `systematic-debugging` · `code-review` 셋이 실제로 겹쳤다.

| 우리 스킬 | 상류 출처 | 분량 |
|---|---|---|
| `vreins-verify` | `verification-before-completion` 파생 | 4KB → 3KB |
| `vreins-debug` | `systematic-debugging` (9파일 41KB) 파생 | 41KB → 5KB |
| `vreins-plan` | `writing-plans` 파생 | |
| `vreins-review` | `requesting-code-review` · `receiving-code-review` 파생 | |
| `vreins-rules` | **우리 것** | |
| `vreins-workflow` | **우리 것** | |
| `vreins-system` | **우리 것** | |

### `vreins-verify` 에서 바꾼 것

    TDD 전제 제거              테스트 프로젝트가 없는 레거시다
    상주 프로세스 항목 추가     파일만 덮으면 안 바뀐다. 재기동해야 한다
    「권한에 막혔을 때」 신설    원본에 없다. 비교 시험에서 실제로 필요했다

### `vreins-debug` 에서 바꾼 것

    9파일 41KB → SKILL.md 하나 5KB
    CI/keychain/codesign 예시   →  설비(L1) → 수신관리 → 편집 → DB → MES(L3)
    「실패 테스트 먼저」          →  「재현 절차를 먼저 적는다」
    되는 것과 견주기 일반론      →  「ABCF 에서 되는데 ABCD 에서 안 되면 차이가 답」

4단계 골격과 「3회 실패하면 구조를 의심한다」는 그대로 살렸다. 거기가 값어치다.

---

## 버린 것

원본 스킬 14종 약 360KB 중 대부분을 안 가져왔다.

| 버린 것 | 분량 | 왜 |
|---|---|---|
| `writing-skills` | 108KB | 스킬 작성법. 메타 문서라 작업자에게 쓰임이 없다 |
| `brainstorming` | 76KB | 전용 서버까지 딸려 온다. 우리 `01-requirements` 가 그 자리다 |
| `subagent-driven-development` | 39KB | 우리 단계 워크플로와 전제가 다르다 |
| `using-superpowers` | 28KB | 방식만 가져오고 문서는 `vreins-rules` 로 새로 썼다 |
| `test-driven-development` | 18KB | **테스트 프로젝트가 없는 레거시**에 Iron Law 를 걸면 매번 예외를 탄다 |
| `using-git-worktrees` | 7KB | 우리 주력이 TFS 다 |
| `finishing-a-development-branch` | 7KB | 〃 git 전용 |
| `dispatching-parallel-agents` | 7KB | 지금 필요 없다 |
| `executing-plans` | 12KB | `vreins-workflow` 와 `03-design.md` 가 그 자리다 |
| `docs\` · `tests\` | — | 원본 개발 이력과 그쪽 스킬 테스트 |
| `.codex-plugin` · `.cursor-plugin` 등 | — | 멀티 툴 배포용. 우리는 Claude Code 하나다 |

**「나중에 쓸지도 모른다」로 남기지 않았다.** 필요해지는 날 다시 가져오면 된다.

## 가져오지 않은 설계

**`<EXTREMELY_IMPORTANT>` 식 강조 주입을 쓰지 않는다.**

2026-09-21 실측에서 원본은 세션 시작에 6,106자를 주입하며 *"1%라도 적용될 것 같으면
반드시 호출하라"* 고 못 박았는데, **실제로 불린 스킬은 14개 중 1개**였다.
`test-driven-development` 의 Iron Law 는 발동조차 안 했고, 유일하게 불린
`brainstorming` 도 자기 HARD-GATE 를 스스로 해제했다.

**강제력은 문구의 세기가 아니라 기계적 장치에서 나온다.** 우리는 훅의 조건부 주입과
`permissions.allow` 로 거는 쪽을 택한다.

다만 **문장 구조는 가져올 값이 있었다** — 금지를 먼저 적고, 이유를 뒤에 붙이고,
「이번만 건너뛸까」 같은 회피로를 미리 막는 방식. `hooks\rules\` 에도 그 방식을 쓴다.
