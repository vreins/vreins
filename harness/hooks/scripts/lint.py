# -*- coding: utf-8 -*-
r"""위키를 검사한다.  python hooks/scripts/lint.py [wiki경로]

**막지 못하면서 초록불을 켜는 검사가 제일 해롭다.** 그래서 여기 있는 것은
전부 「형태」만 본다 — 내용이 맞는지는 판정하지 않는다. 의도를 보려 들면 무너진다.

정본은 skills\vreins-workflow\references\overview.md 하나다. 절 목록을 여기 적지 않는다.
"""
import io, os, re, sys

# 콘솔이 CP949 면 한글 출력에서 죽는다. 환경변수에 기대지 않고 여기서 고정한다.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HARNESS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE = os.path.join(HARNESS, "skills", "vreins-workflow", "references", "overview.md")
VOCAB_DIR = None          # 위키 안 관계.md. 아래에서 채운다
LIMIT_SEC = 4000       # 한 절. 한 번에 읽는 단위가 절이라 여기에 건다
LIMIT_FILE = 15000     # 파일 전체. 경고만 — 넘었다고 틀린 건 아니다
LIFECYCLE = ("skeleton", "production", "deprecated")
REQUIRED = ("type", "system", "aliases", "lifecycle", "description", "owner", "techbase", "updated")

err = []
warn = []


def read(p):
    return io.open(p, encoding="utf-8", newline="").read()


def template_sections():
    """양식의 `## 절 …` 아래 첫 코드펜스에서 `N. 제목` 을 뽑는다.

    양식 본문에는 예시용 `## 2. 연계 시스템` 이 펜스 안에 들어 있어서
    제목줄을 훑으면 그것까지 걸린다. 그래서 목록 블록만 본다."""
    if not os.path.exists(TEMPLATE):
        err.append("양식을 못 찾았다 — %s. 절 검사가 통째로 빠진다" % TEMPLATE)
        return []
    t = read(TEMPLATE)
    m = re.search(r"^## 절 .*?$(.*?)^```", t, re.S | re.M)
    if not m:
        err.append("양식에서 절 목록 블록을 못 읽었다 — 검사가 빠진다")
        return []
    body = t[m.start(1):t.index("```", t.index("```", m.start(1)) + 3)]
    out = []
    for ln in body.split("\n"):
        mm = re.match(r"^(\d+)\.\s+(\S+(?:\s\S+)?)\s\s+", ln)
        if mm:
            out.append((int(mm.group(1)), mm.group(2).strip()))
    if not out:
        err.append("양식 절 목록이 비었다 — 검사가 빠진다")
    return out


def frontmatter(t):
    m = re.match(r"^---\n(.*?)\n---", t, re.S)
    return (m.group(1), m.end()) if m else (None, 0)


def rel_names(fm):
    m = re.search(r"^related:\s*(.*)$", fm, re.M)
    if not m:
        return None
    raw = m.group(1)
    return [x.split("|")[-1].strip() for x in re.findall(r"\[\[([^\]]+)\]\]", raw)]


def table_partners(t):
    """2절 표의 첫 칸에서 [[상대]] 를 뽑는다."""
    m = re.search(r"^## 2\..*?$(.*?)(?=^## 3\.)", t, re.S | re.M)
    if not m:
        return None
    out = []
    for ln in m.group(1).split("\n"):
        mm = re.match(r"^\|\s*\[\[([^\]]+)\]\]\s*\|", ln)
        if mm:
            v = mm.group(1).split("|")[-1].strip()
            if v not in out:
                out.append(v)
    return out


def vocab(wiki):
    p = os.path.join(wiki, "관계.md")
    if not os.path.exists(p):
        warn.append("관계.md 가 없다 — 태그 검사를 건너뛴다")
        return None
    t = read(p)
    v = set(re.findall(r"^\|\s*`([^`]+)`\s*\|", t, re.M))
    # 표 모양이 바뀌면 여기가 조용히 0개가 되고 태그 검사가 멈춘다.
    # 막지 못하면서 초록불을 켜는 검사가 제일 해롭다 — 적으면 오류를 낸다.
    if len(v) < 8:
        err.append("관계.md 에서 어휘를 %d개만 뽑았다 — 표 모양이 바뀐 것 같다. "
                   "태그 검사가 멈춘다" % len(v))
    return v


def check_overview(p, rel, want, vc):
    t = read(p)
    fm, _ = frontmatter(t)
    if fm is None:
        err.append("%s : 머리말이 없다" % rel)
        return

    # 머리말이 YAML 로 깨졌나. 값이 있는 키 바로 뒤에 리스트 항목이 오면
    # 그 항목은 소속을 잃고, 옵시디언은 머리말을 통째로 못 읽는다 —
    # related 가 링크로 안 잡혀 그래프에서 선이 사라진다. 눈으로는 멀쩡해 보인다.
    fl = fm.split(chr(10))
    for n2 in range(1, len(fl)):
        if fl[n2].strip().startswith("- ") and re.match(r"^[^\s-].*?:\s*\S", fl[n2 - 1]):
            err.append("%s : 머리말이 깨졌다 — `%s` 뒤의 `%s` 가 소속을 잃었다"
                       % (rel, fl[n2 - 1].strip(), fl[n2].strip()))
            break
    # related 가 값이 통째로 [[...]] 인가. 문자열 안에 섞이면 링크로 안 잡힌다.
    rl = re.search(r"^related:\s*(.*)$", fm, re.M)
    if rl and rl.group(1).strip():
        for it in re.findall(r'"([^"]*)"', rl.group(1)):
            if not re.fullmatch(r"\[\[[^\]]+\]\]", it.strip()):
                err.append("%s : related 의 `%s` 는 값 전체가 [[...]] 가 아니다 — 링크로 안 잡힌다"
                           % (rel, it[:40]))

    for k in REQUIRED:
        if not re.search(r"^%s:" % k, fm, re.M):
            err.append("%s : 머리말에 `%s` 가 없다" % (rel, k))
    m = re.search(r"^lifecycle:\s*(\S+)", fm, re.M)
    if m and m.group(1) not in LIFECYCLE:
        err.append("%s : lifecycle `%s` 는 없는 값이다 — %s 중 하나" % (rel, m.group(1), " · ".join(LIFECYCLE)))

    got = [(int(x.group(1)), x.group(2).strip()) for x in re.finditer(r"^## (\d+)\.\s*(.+)$", t, re.M)]
    if want and got != want:
        diff = []
        for i in range(max(len(want), len(got))):
            w = want[i] if i < len(want) else None
            g = got[i] if i < len(got) else None
            if w != g:
                diff.append("%s절은 「%s」 이어야 하는데 「%s」"
                            % (w[0] if w else "?", w[1] if w else "(없다)", g[1] if g else "(없다)"))
        err.append("%s : 절 구성이 양식과 다르다 — %s" % (rel, " · ".join(diff[:3])))

    names = rel_names(fm)
    part = table_partners(t)
    if names is not None:
        if part is None:
            err.append("%s : related 가 있는데 2절을 못 찾았다" % rel)
        else:
            only_fm = [x for x in names if x not in part]
            only_tb = [x for x in part if x not in names]
            if only_fm:
                err.append("%s : 머리말 related 에만 있다 — %s. 2절 표에 줄을 더한다" % (rel, " · ".join(only_fm)))
            if only_tb:
                err.append("%s : 2절 표에만 있다 — %s. 머리말 related 에 이름을 더한다" % (rel, " · ".join(only_tb)))
        if vc:
            m2 = re.search(r"^## 2\..*?$(.*?)(?=^## 3\.)", t, re.S | re.M)
            for ln in (m2.group(1).split("\n") if m2 else []):
                # 위키링크의 [[A|B]] 안에도 | 가 있다. 칸을 자르기 전에 가린다.
                safe = re.sub(r"\[\[[^\]]*\]\]", lambda m: m.group(0).replace("|", ""), ln)
                c = [x.strip().replace("", "|") for x in safe.strip().strip("|").split("|")]
                if len(c) < 6 or not c[0].startswith("[["):
                    continue
                for tag in (c[1] + " " + c[2] + " " + c[3]).split():
                    if tag in ("—", "-", ""):
                        continue
                    if tag not in vc:
                        warn.append("%s : 태그 `%s` 가 관계.md 에 없다 — 새 말이면 거기 한 줄 더한다" % (rel, tag))

    # 한도를 파일이 아니라 절에 건다. 세션 시작에 올라가는 것은 related 이름뿐이고
    # 본문은 단계가 부를 때 **그 절만** 열린다 — 재는 대상이 파일이 아니라 절이다.
    heads = [(x.start(), x.group(2).strip()) for x in re.finditer(r"^## (\d+)\.\s*(.+)$", t, re.M)]
    for k, (st, ttl) in enumerate(heads):
        en = heads[k + 1][0] if k + 1 < len(heads) else len(t)
        # 자동구역은 길이에서 뺀다. 기계가 채우고 100건 상한이 따로 걸려 있어
        # 사람이 줄일 수 있는 자리가 아니다 — 못 고치는 것을 오류로 내면 무시하게 된다.
        body = t[st:en]
        for a in re.finditer(r"<!-- auto:.*?-->(.*?)<!-- /auto -->", body, re.S):
            body = body.replace(a.group(0), "")
        ln = len(body)
        if ln > LIMIT_SEC:
            err.append("%s : 「%s」 가 %s자로 한 절 한도 %s자를 넘었다 — 양식의 덜어내는 순서대로 줄인다"
                       % (rel, ttl, format(ln, ","), format(LIMIT_SEC, ",")))
    if len(t) > LIMIT_FILE:
        warn.append("%s : 파일이 %s자다. 절마다는 한도 안이지만 통째로 크다 — 시스템이 하나가 아닌지 의심한다"
                    % (rel, format(len(t), ",")))


def definitions(wiki):
    """이 PC 의 시스템 정의({루트}\\systems\\{유형}\\{코드}.json)와 위키 시스템을 대조한다.

    둘은 답하는 질문이 다르다 — 정의는 「이 PC 에서 진입할 수 있는 것」, 위키는 「팀이 아는 것」.
    그래서 비대칭으로 본다.
      정의만 있다   오류.  산출물이 갈 자리가 없다 — 위키에 폴더를 만든다 (_sample 을 베낀다)
      위키만 있다   정보.  내가 안 맡은 시스템일 뿐이다. 맡았으면 런처 [시스템 설정] 에서 등록한다

    플러그인\\systems\\ 는 더 보지 않는다 — 2026-09-22 회의로 시스템 정보는 플러그인에
    넣지 않기로 했고, 그 층은 언제나 비어 있었다."""
    root = os.environ.get("VREINS_ROOT") or r"C:\vReins"
    sysdir = os.path.join(root, "systems")
    if not os.path.isdir(sysdir):
        warn.append("시스템 정의 폴더가 없다 — %s. 이 PC 에서는 어느 시스템으로도 세션을 못 연다" % sysdir)
        return
    reg = set()
    for t in sorted(os.listdir(sysdir)):
        d = os.path.join(sysdir, t)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith(".json") and not f.endswith(".local.json"):
                reg.add((t, f[:-5]))
    wk = set()
    for t in sorted(os.listdir(wiki)):
        p = os.path.join(wiki, t)
        if not os.path.isdir(p) or t.startswith((".", "_")):
            continue
        for c in sorted(os.listdir(p)):
            if c != "COMMON" and os.path.isfile(os.path.join(p, c, c + "-OVERVIEW.md")):
                wk.add((t, c))
    for t, c in sorted(reg - wk):
        err.append("시스템 정의 systems/%s/%s.json 이 있는데 위키에 %s/%s/%s-OVERVIEW.md 가 없다 — "
                   "산출물이 갈 자리가 없다. _sample/ 을 베껴 만든다" % (t, c, t, c, c))
    missing = sorted(wk - reg)
    if missing:
        warn.append("이 PC 에 시스템 정의가 없는 위키 시스템 %d개 — %s. 안 맡은 것이면 정상이고, "
                    "맡은 것이면 런처 [시스템 설정] 에서 등록한다"
                    % (len(missing), " · ".join("%s/%s" % x for x in missing)))


def main(wiki):
    want = template_sections()
    definitions(wiki)
    vc = vocab(wiki)
    n = 0
    for root, d, fs in os.walk(wiki):
        if ".git" in root:
            continue
        for f in fs:
            if not f.endswith(".md"):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, wiki)
            raw = io.open(p, "rb").read()
            if raw.startswith(b"\xef\xbb\xbf"):
                err.append("%s : BOM 이 붙었다 — UTF-8 BOM 없이 저장한다" % rel)
            if b"\r\n" in raw:
                err.append("%s : CRLF 가 섞였다 — LF 로 저장한다" % rel)
            if f == os.path.basename(root) + "-OVERVIEW.md":
                # 파일 이름이 {시스템코드}-OVERVIEW.md 다. 그냥 overview.md 였을 때는 12개가 전부 같은 이름이라
                # 옵시디언에서 [[MESD]] 가 해결되지 않아 그래프에 선이 안 그어졌다.
                # 짧은 [[MESD]] 는 머리말 aliases 가 받는다.
                n += 1
                check_overview(p, rel, want, vc)

    print("overview %d개를 봤다." % n)
    for e in err:
        print("  [오류] " + e)
    for w in warn:
        print("  [경고] " + w)
    if not err and not warn:
        print("  어긋난 것 없다.")
    return 1 if err else 0


def wiki_from_env():
    """위키 경로를 인자로 안 줬으면 VREINS_WIKI_ROOT 를 본다. 없으면 멈춘다 — 경로를 지어내지 않는다."""
    w = os.environ.get("VREINS_WIKI_ROOT")
    if not w or not os.path.isdir(w):
        sys.exit("위키 경로를 첫 인자로 주거나 VREINS_WIKI_ROOT 를 둔다")
    return w


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else wiki_from_env()))
