---
description: 05 테스트 — 확인한다. 돌린 명령과 그 출력을 남긴다
argument-hint: [작업 제목. 비우면 진행 중인 세션을 찾는다]
---

`vreins-workflow` 스킬을 읽고 **05 Testing** 단계를 진행한다.

작업: $ARGUMENTS

`04-development-{제목}.md` 가 **없으면 멈춘다.**

읽는 지침은 `guideline-TechStack.md` · `guideline-Linter.md` 다 (4절 표).

## 이 단계의 핵심

**돌린 것만 적는다.** 「통과할 것으로 보인다」는 테스트 결과가 아니다.
`vreins-verify` 스킬을 읽고 그 기준대로 쓴다 — 명령과 출력이 문서에 있어야 한다.

실패한 것은 **실패했다고 쓴다.** 덮으면 다음 사람이 통과한 줄 안다.

## 끝내는 법

승인받은 뒤 커밋한다. 다음은 `/vreins-deployment` 이고, 우리 환경에서는
매뉴얼 작성 정도로 끝나는 경우가 많다.
