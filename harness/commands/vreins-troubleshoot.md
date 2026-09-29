---
description: 장애 — 한 장으로 끝낸다. 단계를 나누지 않는다
argument-hint: [증상. 로그 한 줄이라도 좋다]
---

`vreins-workflow` 스킬의 **TS Troubleshooting** 을 진행한다.
같이 `vreins-debug` 스킬을 읽는다 — 그쪽이 실행 절차다.

증상:

$ARGUMENTS

비어 있으면 **묻는다.** 증상을 지어내지 않는다.

## 여섯 단계를 타지 않는다

장애는 `TS-troubleshooting-{제목}.md` **한 장**으로 끝낸다.
요구사항·설계 문서를 만들지 않는다.

읽는 지침은 `guideline-TechStack.md` · `guideline-Architecture.md` 다 (4절 표).

## 고치기 전에 원인을 찾는다

로그 한 줄에서 원인 지점까지 거슬러 오른다.
**원인을 못 찾은 채로 고치지 않는다** — 증상이 사라져도 고친 것이 아니다.

추측으로 답하고 있다는 신호가 오면 멈추고 확인한다
(`handling-unknowns`). 테이블·컬럼의 뜻은 COMMENT 가 정본이고,
프레임워크 내부 동작은 이름으로 짐작하지 않는다.

## 끝내는 법

`vreins-verify` 스킬을 쓴다 — 재현하던 것이 실제로 안 나는지 돌려서 확인한다.
승인받은 뒤 커밋한다.
