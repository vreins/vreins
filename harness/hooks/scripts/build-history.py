#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""각 overview.md 5절의 「이력」 구역을 짓는다.  손으로 고치지 않는다.

    python build-history.py {위키루트} [--write]

기본은 dry-run 이다. 실제로 쓰려면 --write 를 준다 —
잘못 돌려도 파일이 안 상하는 쪽이 기본이어야 한다.

정본은 폴더 이름이다. `ls {유형}/{시스템}/{연도}/` 가 주는 것을 그대로 적는다.
요약을 붙이지 않는다 — 폴더명에 날짜·SR번호·제목이 이미 들어 있고,
요약까지 붙이면 overview 가 8,000자 한도를 넘긴다.
"""

import io
import os
import re
import sys

# 콘솔이 CP949 면 한글 출력에서 죽는다. 환경변수에 기대지 않고 여기서 고정한다.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MAX = 100

OPEN_RE = re.compile(r"<!--\s*auto:이력[^\n]*?-->")
CLOSE = "<!-- /auto -->"
OPEN_LINE = "<!-- auto:이력  손으로 고치지 않는다. 생성기가 ls 로 채운다 -->"
HEAD = "### 이력"
EMPTY = "_없다._"


def render(bands, nl):
    """대역별로 묶어 찍는다. 대역이 곧 화면 묶음이라 사람이 훑을 단위가 된다."""
    if not bands:
        return EMPTY
    out = []
    for b in sorted(bands, key=lambda x: (x.startswith("("), x)):
        out.append("**%s** (%d건)" % (b, len(bands[b])))
        out.append("")
        out.extend("- " + n for n in bands[b])
        out.append("")
    return nl.join(out).rstrip()

SEC5 = re.compile(r"^## 5\.", re.M)
SEC = re.compile(r"^## ", re.M)
YEAR = re.compile(r"^\d{4}$")
# 「0N-」 로 시작하는 단계 문서. readme 는 하이픈 없는 것도 받는다 —
# 규약은 `readme-*.md` 지만 옛 폴더에 `readme.md` 만 있는 것이 섞여 있어
# 그것을 작업 폴더가 아니라고 판정하면 이력에서 통째로 사라진다.
STEP = re.compile(r"^0\d-.*\.md$", re.I)
README = re.compile(r"^readme(-.*)?\.md$", re.I)

YMD = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:\D|$)")
YYMM = re.compile(r"^(\d{2})(\d{2})(?:\D|$)")


# ---------------------------------------------------------------- 머리말

def read(path):
    """원본 줄바꿈을 그대로 들고 온다 — 다시 쓸 때 섞이면 안 된다."""
    return io.open(path, encoding="utf-8", newline="").read()


def newline_of(text):
    """그 파일이 쓰던 줄바꿈을 따른다. 한 파일 안에 두 종류가 섞이면
    프론트매터 파서가 깨진다 — 실제로 한 번 겪었다."""
    return "\r\n" if "\r\n" in text else "\n"


def frontmatter(path):
    """--- ... --- 사이를 아주 얕게 읽는다. 스칼라만.

    yaml 을 쓰지 않는 이유 — 표준 라이브러리 밖으로 나가면 훅이 도는
    서버마다 설치를 맞춰야 한다. 여기서 필요한 것은 `pin` 한 줄이다."""
    try:
        txt = read(path)
    except Exception:
        return {}
    txt = txt.replace("\r\n", "\n")
    if not txt.startswith("---"):
        return {}
    end = txt.find("\n---", 3)
    if end < 0:
        return {}
    fm = {}
    for line in txt[3:end].split("\n"):
        if not line.strip() or line[:1] in (" ", "\t", "#"):
            continue
        m = re.match(r"^([A-Za-z_가-힣0-9]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def is_pinned(folder):
    """작업 폴더 안 readme 아무 것이나 pin: true 면 고정이다."""
    for name in sorted(os.listdir(folder)):
        if not README.match(name):
            continue
        v = frontmatter(os.path.join(folder, name)).get("pin", "")
        if v.strip().strip('"').strip("'").lower() == "true":
            return True
    return False


# ---------------------------------------------------------------- 모으기

def sortkey(folder):
    """폴더명 앞의 YYYY-MM-DD 또는 YYMM 을 YYYYMMDD 로 편다.

    YYMM 을 먼저 보면 `2026-09-16-…` 의 `20`/`26` 을 연·월로 읽어 버린다.
    그래서 긴 쪽부터 본다. 달이 13 이상이면 YYMM 이 아니다."""
    m = YMD.match(folder)
    if m:
        return m.group(1) + m.group(2) + m.group(3)
    m = YYMM.match(folder)
    if m and 1 <= int(m.group(2)) <= 12:
        return "20" + m.group(1) + m.group(2) + "00"
    return ""


def is_work(folder):
    try:
        names = os.listdir(folder)
    except OSError:
        return False
    for n in names:
        if not os.path.isfile(os.path.join(folder, n)):
            continue
        if README.match(n) or STEP.match(n):
            return True
    return False


def screens(wdir):
    """작업 폴더의 `화면코드:` 를 읽는다. 폴더는 대역으로 거칠게 묶고
    목록은 화면으로 정밀하게 묶는다 — 「이 화면 앞서 누가 고쳤나」가
    실제로 필요한 축이고, 실측 48건 중 33건(69%)이 남이 이미 손댄 화면이었다."""
    for f in sorted(os.listdir(wdir)):
        if not f.startswith("readme-"):
            continue
        try:
            t = io.open(os.path.join(wdir, f), encoding="utf-8", newline="").read(2500)
        except Exception:
            return []
        m = re.search(r"^화면코드:\s*\[(.*?)\]", t, re.M)
        if not m:
            return []
        return [x.strip().strip(chr(34)).strip(chr(39)) for x in re.split(r"[,\s]+", m.group(1)) if x.strip()]
    return []


def collect(sysdir):
    """{시스템}/{대역}/{작업} 을 모아 **화면코드별로** 묶는다.

    폴더 축(대역)과 목록 축(화면)이 다르다. 폴더는 10년 뒤 600건이
    한 자리에 안 쌓이게 하는 것이고, 목록은 같은 화면 이력을 붙여 두는 것이다.
    화면코드가 없는 작업은 `(화면 없음)` 으로 간다 — 실측 26건 중 4건."""
    byscreen = {}
    for band in sorted(os.listdir(sysdir)):
        bdir = os.path.join(sysdir, band)
        if not os.path.isdir(bdir) or band in ("_manual", "COMMON"):
            continue
        if band.startswith("."):
            continue
        for work in sorted(os.listdir(bdir)):
            wdir = os.path.join(bdir, work)
            if work.startswith((".", "_")) or not os.path.isdir(wdir):
                continue
            if not is_work(wdir):
                continue
            key = sortkey(work)
            row = (is_pinned(wdir), key, work)
            for sc in (screens(wdir) or ["(화면 없음)"]):
                byscreen.setdefault(sc, []).append(row)
    out = {}
    for sc, rows in byscreen.items():
        dated = [r for r in rows if r[1]]
        undated = [r for r in rows if not r[1]]
        dated.sort(key=lambda r: (r[1], r[2]), reverse=True)
        undated.sort(key=lambda r: r[2], reverse=True)
        rows = dated + undated
        out[sc] = [r[2] for r in ([x for x in rows if x[0]] + [x for x in rows if not x[0]])]
    total = sum(len(v) for v in out.values())
    if total > MAX:
        for k in sorted(out, reverse=True):
            while total > MAX and out[k]:
                out[k].pop(); total -= 1
    return out


def block(names, nl):
    body = [OPEN_LINE]
    body += ["- " + n for n in names] if names else [EMPTY]
    body.append(CLOSE)
    return nl.join(body)


def section5_span(text):
    """5절의 [시작, 끝) 를 준다. 끝은 다음 `## ` 절 머리 또는 파일 끝."""
    m = SEC5.search(text)
    if not m:
        return None
    nxt = SEC.search(text, m.end())
    return (m.start(), nxt.start() if nxt else len(text))


def apply(text, names):
    """구역 안만 갈아 끼운다. 없으면 5절 끝에 새로 만든다.

    반환 (새 본문, 무엇을 했는지). 5절이 없으면 (None, 사유)."""
    nl = newline_of(text)
    span = section5_span(text)
    if not span:
        return None, "5절이 없다"
    s, e = span

    m = OPEN_RE.search(text)
    if m:
        close = text.find(CLOSE, m.end())
        if close < 0:
            return None, "구역이 열리고 안 닫혔다 — 손으로 본다"
        if not (s <= m.start() < e):
            return None, "구역이 5절 밖에 있다 — 손으로 옮긴다"
        # 여는 표시 줄과 닫는 표시는 그대로 두고 사이만 바꾼다.
        inner = nl + render(names, nl) + nl
        new = text[:m.end()] + inner + text[close:]
        return new, "갱신"

    head, tail = text[:e], text[e:]
    ins = HEAD + nl + nl + render(names, nl) + nl
    # 있던 빈 줄을 지우지 않는다. 모자라면 보탠다.
    if head.endswith(nl + nl):
        pre = ""
    elif head.endswith(nl):
        pre = nl
    else:
        pre = nl + nl
    return head + pre + ins + (nl if tail else "") + tail, "신설"


# ---------------------------------------------------------------- 돌기

def run(root, write):
    total = 0
    touched = 0
    skipped = []
    # 유형을 목록으로 박지 않는다. 위키 밑의 폴더가 곧 유형이다.
    #
    # 한때 유형 넷을 목록으로 박아 두었다. 그 넷은 **쓰던 곳의 넷**이라
    # 이 플러그인을 받아 쓰는 다른 곳에는 맞지 않고, 같은 곳 안에서도 유형을
    # 새로 만들면 조용히 빠진다 — 오류가 아니라 「이력이 안 붙네」로만 보인다.
    #
    # 거르는 기준은 아래 시스템 층과 같다. _로 시작하는 것, .git, COMMON.
    for typ in sorted(os.listdir(root)):
        tdir = os.path.join(root, typ)
        if typ.startswith("_") or typ in (".git", "COMMON") or not os.path.isdir(tdir):
            continue
        for name in sorted(os.listdir(tdir)):
            sysdir = os.path.join(tdir, name)
            if name.startswith("_") or name == ".git" or not os.path.isdir(sysdir):
                continue
            if name == "COMMON":
                # 유형 공통이지 시스템이 아니다. 이력이 붙을 자리가 없다.
                continue
            ov = os.path.join(sysdir, os.path.basename(sysdir) + "-OVERVIEW.md")
            key = typ + "/" + name
            if not os.path.isfile(ov):
                skipped.append((key, "시스템 문서가 없다"))
                continue
            names = collect(sysdir)
            cnt = sum(len(v) for v in names.values())
            total += cnt
            text = read(ov)
            new, what = apply(text, names)
            if new is None:
                skipped.append((key, what))
                print("  %-22s %3d건  건너뜀 — %s" % (key, cnt, what))
                continue
            if new == text:
                print("  %-22s %3d건  그대로" % (key, cnt))
                continue
            touched += 1
            print("  %-22s %3d건  %s%s" % (key, cnt, what,
                                           "" if write else " (dry-run)"))
            for b in sorted(names):
                print("      %-6s %d건" % (b, len(names[b])))
            if write:
                with io.open(ov, "w", encoding="utf-8", newline="\n") as f:
                    f.write(new)

    print("")
    print("이력 %d건 · %s %d개" % (total, "고친 파일" if write else "고칠 파일", touched))
    if skipped:
        print("건너뛴 것 %d개 — 손이 필요하다" % len(skipped))
        for key, why in skipped:
            print("  %-22s %s" % (key, why))
    if not write:
        print("dry-run 이다. 실제로 쓰려면 --write 를 준다.")


def wiki_from_env():
    """위키 경로를 인자로 안 줬으면 VREINS_WIKI_ROOT 를 본다. 없으면 멈춘다 — 경로를 지어내지 않는다."""
    w = os.environ.get("VREINS_WIKI_ROOT")
    if not w or not os.path.isdir(w):
        sys.exit("위키 경로를 첫 인자로 주거나 VREINS_WIKI_ROOT 를 둔다")
    return w


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    bad = [f for f in flags if f not in ("--write", "--dry-run")]
    if bad:
        sys.exit("모르는 인자다 — %s" % " ".join(bad))
    if "--write" in flags and "--dry-run" in flags:
        sys.exit("--write 와 --dry-run 을 같이 줄 수 없다")
    run(args[0] if args else wiki_from_env(), "--write" in flags)
