# -*- coding: utf-8 -*-
"""각 시스템 문서 5절의 「읽을 문서」 목차를 찍는다.

  python build-docindex.py {wiki} [--write]

**손으로 적지 않는다.** 두 원본을 합쳐 만든다.

    종류 → 단계    하네스 vreins-rules SKILL.md 의 표 하나
    문서 → 종류    각 문서 머리말의 `종류:` · `강도:` · `description:`

그래서 정책을 바꾸면 표 한 줄만 고치고 목차 열둘이 따라온다.
문서를 새로 넣으면 머리말만 적으면 목차에 들어온다.
"""
import io, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HARNESS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TABLE = os.path.join(HARNESS, "skills", "vreins-rules", "SKILL.md")
OPEN, CLOSE = "<!-- auto:읽을문서", "<!-- /auto -->"
FOPEN = "<!-- auto:폴더목록"
ORD = {"필수": 0, "권장": 1, "참조": 2}


def read(p):
    return io.open(p, encoding="utf-8", newline="").read()


def stage_map():
    """양식이 아니라 헌법에서 읽는다. 여기 옮겨 적으면 두 벌이 된다."""
    t = read(TABLE)
    m = re.search(r"^종류 +단계 +무엇$(.*?)^```", t, re.S | re.M)
    if not m:
        print("  [오류] vreins-rules 에서 종류 표를 못 읽었다 — 목차를 못 만든다")
        return {}
    out = {}
    for ln in m.group(1).splitlines():
        if not ln.strip() or ln.lstrip().startswith("─"):
            continue
        # 칸을 「공백 둘 이상」으로 가른다. 단계 값 안에 ` · ` 가 있어서
        # 공백 하나로 자르면 `02` 만 떼어 온다 — 실제로 14종 중 6종만 읽혔다.
        cols = re.split(r" {2,}", ln.strip())
        if len(cols) >= 2:
            out[cols[0].strip()] = cols[1].strip()
    return out


def meta(p):
    t = read(p)[:2500]
    fm = re.match(r"^---\n(.*?)\n---", t, re.S)
    def g(k):
        if not fm:
            return ""
        x = re.search(r"^%s:\s*(.+)$" % k, fm.group(1), re.M)
        return x.group(1).strip() if x else ""
    kind = g("종류")
    if not kind:
        # 지침은 파일 이름이 종류를 말한다. 머리말이 없어도 걸린다.
        mm = re.search(r"-(TechStack|Architecture|Boilerplate|Linter)\.md$", os.path.basename(p))
        if mm:
            kind = mm.group(1)
        elif "-reference-" in os.path.basename(p):
            kind = "reference"
    return kind, (g("강도") or "—"), g("description")


GUIDE = re.compile(r"^(.+?)-(TechStack|Architecture|Boilerplate|Linter|reference-.+)\.md$")


def techbase_of(ov):
    """시스템 문서 머리말의 `techbase`. 없거나 비면 빈 목록.

    인라인(`techbase: [A, B]`)과 블록(`techbase:` 아래 `  - A`) 둘 다 받는다 —
    옵시디언 속성 편집기가 저장하면 블록으로 바뀐다. 실제로 SICB 가 그렇다."""
    fm = re.match(r"^---\n(.*?)\n---", read(ov)[:2500], re.S)
    if not fm:
        return []
    m = re.search(r"^techbase:[ \t]*(.*)$", fm.group(1), re.M)
    if not m:
        return []
    v = m.group(1).strip()
    if v.startswith("["):
        return [x.strip().strip("'\"") for x in v.strip("[]").split(",") if x.strip()]
    out = []
    for ln in fm.group(1)[m.end():].split("\n")[1:]:   # [0] 은 `techbase:` 줄의 꼬리(빈 문자열)다
        mm = re.match(r"^\s+-\s*(\S.*?)\s*$", ln)
        if not mm:
            break
        out.append(mm.group(1).strip("'\""))
    return out


def collect(sysdir, typ, wiki, techbase):
    """유형 공통 `_manual/` 과 시스템 `_manual/` 을 합친다.

    공통 폴더의 **지침**(`{기술기반}-*.md`)은 이 시스템의 `techbase` 에 든 기술기반 것만 싣는다 —
    한 유형에 기술기반이 여럿이고(APP 은 Django 와 Flutter), techbase 가 빈 시스템도 있다.
    안 거르면 Java 시스템 목차에 Django Linter 가 「필수」로 찍힌다. 받은 문서는 거르지 않는다."""
    common = os.path.join(wiki, typ, "COMMON", "_manual")
    own = os.path.join(sysdir, "_manual")
    rows = []
    for base, pref, tag in ((common, "../COMMON/_manual/", "공통"), (own, "_manual/", "")):
        if not os.path.isdir(base):
            continue
        for f in sorted(os.listdir(base)):
            # -INDEX 는 이 목차가 가리키는 **목록 파일**이지 읽을 문서가 아니다.
            # 넣으면 「종류가 안 붙은 것」 단에 자기 자신이 뜬다.
            if "OVERVIEW" in f or f.endswith("-INDEX.md") or not f.endswith(".md"):
                continue
            g = GUIDE.match(f)
            if tag and g and g.group(1) not in techbase:
                continue
            k, s, d = meta(os.path.join(base, f))
            rows.append((f[:-3], pref + f, k, s, d, tag))
    return rows


def block(rows, smap, cap):
    """세 단으로 가른다 — 단계가 부르는 것 · 판단해서 여는 것 · 그 밖.

    첫 단은 안 읽으면 안 된다. 둘째 단은 **읽을지를 모델이 정한다** —
    설명을 보고 이번 건에 걸리는지 판단한다. 셋째 단은 목록만 둔다.
    셋을 한 표에 섞으면 「어차피 다 참고」가 되어 아무것도 안 읽힌다."""
    if not rows:
        return "_읽을 문서가 없다. 유형 공통에도 시스템 밑에도 한 건이 없다._"

    must, judge, rest = [], [], []
    for r in rows:
        when = smap.get(r[2], "")
        (must if re.match(r"^\d", when) else judge if when else rest).append((r, when))
    must.sort(key=lambda x: (ORD.get(x[0][3], 3), x[0][0]))
    judge.sort(key=lambda x: x[0][0])
    rest.sort(key=lambda x: x[0][0])

    def tab(items, cols):
        out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for (nm, lnk, k, st, d, tag), when in items:
            cell = "[%s](%s)%s" % (nm, lnk, " `공통`" if tag else "")
            row = [cell, when, st, d or "—"] if len(cols) == 4 else [cell, st, d or "—"]
            out.append("| " + " | ".join(row) + " |")
        return "\n".join(out)

    P = []
    if must:
        P.append("**단계가 부르면 읽는다** — 안 읽고 그 단계를 끝내지 않는다.\n")
        P.append(tab(must[:cap], ["문서", "언제", "강도", "무엇이 들었나"]))
        if len(must) > cap:
            P.append("\n나머지 %d건은 그 폴더의 `-INDEX` 가 갖는다." % (len(must) - cap))
    if judge:
        P.append("\n**걸릴 때만 연다** — 설명을 보고 **이번 건에 해당하는지 스스로 정한다.**\n")
        P.append(tab(judge, ["문서", "강도", "무엇이 들었나"]))
    if rest:
        P.append("\n**종류가 안 붙은 것** — 머리말에 `종류:` 를 적으면 위 두 단으로 간다.\n")
        P.append(tab(rest, ["문서", "강도", "무엇이 들었나"]))
    P.append("\n**여기 없는 것을 찾을 때**는 `_manual/` 과 `COMMON/_manual/` 의 "
             "`description` 을 훑는다 — 파일을 열지 않고 한 줄로 고른다.")
    return "\n".join(P)


def apply(text, body):
    nl = "\r\n" if "\r\n" in text else "\n"
    m = re.search(re.escape(OPEN) + r".*?-->", text)
    if m:
        c = text.find(CLOSE, m.end())
        if c < 0:
            return None, "구역이 열리고 안 닫혔다"
        return text[:m.end()] + nl + body + nl + text[c:], "갱신"
    i = text.find("## 5.")
    if i < 0:
        return None, "5절이 없다"
    j = text.find("### 이력", i)
    if j < 0:
        j = len(text)
    head = "**읽을 문서** — 강도는 「어기면 안 되나」고, 「언제」는 「읽어야 하나」다."
    ins = (head + nl + nl + OPEN + "  손으로 고치지 않는다. build-docindex.py 가 찍는다 -->"
           + nl + body + nl + CLOSE + nl + nl)
    return text[:j] + ins + text[j:], "신설"


def folder_block(base, smap):
    """`_manual/` 폴더 목록. 그 폴더에 있는 것 전부를 종류별로 묶는다."""
    rows = []
    for f in sorted(os.listdir(base)):
        # 자기 자신(-INDEX)은 뺀다. 목록이 목록을 가리키면 「종류가 없다」 단에 늘 한 줄이 남는다.
        if "OVERVIEW" in f or f.endswith("-INDEX.md") or not f.endswith(".md"):
            continue
        k, st, d = meta(os.path.join(base, f))
        rows.append((f, k or "—", st, d))
    if not rows:
        return "_비었다. 받은 문서도 지침도 아직 없다._"
    groups = {}
    for f, k, st, d in rows:
        groups.setdefault(k, []).append((f, st, d))
    out = []
    for k in sorted(groups, key=lambda x: (x == "—", x)):
        when = smap.get(k, "부를 때" if k != "—" else "종류가 없다")
        out.append("**%s** · %s · %d건\n" % (k, when, len(groups[k])))
        out.append("| 문서 | 강도 | 무엇이 들었나 |")
        out.append("|---|---|---|")
        for f, st, d in groups[k]:
            out.append("| [%s](%s) | %s | %s |" % (f[:-3], f, st, d or "—"))
        out.append("")
    return "\n".join(out).rstrip()


def apply_folder(text, body):
    nl = "\r\n" if "\r\n" in text else "\n"
    m = re.search(re.escape(FOPEN) + r".*?-->", text)
    if m:
        c = text.find(CLOSE, m.end())
        if c < 0:
            return None, "구역이 열리고 안 닫혔다"
        return text[:m.end()] + nl + body + nl + text[c:], "갱신"
    i = text.find("\n## ")
    if i < 0:
        i = len(text)
    ins = (nl + FOPEN + "  손으로 고치지 않는다. build-docindex.py 가 찍는다 -->"
           + nl + body + nl + CLOSE + nl)
    return text[:i] + ins + text[i:], "신설"


def folder_index(sysdir, name, smap, write):
    """`_manual/{이름}-INDEX.md` 의 폴더 목록도 찍는다.

    여기가 손글씨로 남아 있으면 문서가 늘 때 제일 먼저 낡는다 —
    실측으로 여덟 개가 전부 손으로 적혀 있었다."""
    base = os.path.join(sysdir, "_manual")
    mo = os.path.join(base, name + "-INDEX.md")
    if not os.path.isdir(base) or not os.path.isfile(mo):
        return 0
    new, what = apply_folder(read(mo), folder_block(base, smap))
    if new is None or new == read(mo):
        return 0
    print("      _manual 목록  %s%s" % (what, "" if write else " (dry-run)"))
    if write:
        io.open(mo, "w", encoding="utf-8", newline="\n").write(new)
    return 1


def main(wiki, write):
    smap = stage_map()
    if not smap:
        return 1
    print("종류 %d개를 읽었다 — %s" % (len(smap), " · ".join(sorted(smap))))
    touched = 0
    for typ in sorted(os.listdir(wiki)):
        tdir = os.path.join(wiki, typ)
        if not os.path.isdir(tdir) or typ.startswith((".", "_")):
            continue
        for name in sorted(os.listdir(tdir)):
            sysdir = os.path.join(tdir, name)
            if not os.path.isdir(sysdir) or name in ("COMMON",) or name.startswith((".", "_")):
                continue
            ov = os.path.join(sysdir, name + "-OVERVIEW.md")
            if not os.path.isfile(ov):
                print("  %-22s 시스템 문서가 없다" % (typ + "/" + name))
                continue
            rows = collect(sysdir, typ, wiki, techbase_of(ov))
            cap = 9 if len(rows) > 16 else 16
            new, what = apply(read(ov), block(rows, smap, cap))
            key = typ + "/" + name
            if new is None:
                print("  %-22s %2d건  건너뜀 — %s" % (key, len(rows), what))
                continue
            touched += folder_index(sysdir, name, smap, write)
            if new == read(ov):
                print("  %-22s %2d건  그대로" % (key, len(rows)))
                continue
            print("  %-22s %2d건  %s%s" % (key, len(rows), what, "" if write else " (dry-run)"))
            if write:
                io.open(ov, "w", encoding="utf-8", newline="\n").write(new)
            touched += 1
    print("\n고칠 파일 %d개%s" % (touched, "" if write else "  — 실제로 쓰려면 --write"))
    return 0


def wiki_from_env():
    """위키 경로를 인자로 안 줬으면 VREINS_WIKI_ROOT 를 본다. 없으면 멈춘다 — 경로를 지어내지 않는다."""
    w = os.environ.get("VREINS_WIKI_ROOT")
    if not w or not os.path.isdir(w):
        sys.exit("위키 경로를 첫 인자로 주거나 VREINS_WIKI_ROOT 를 둔다")
    return w


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    sys.exit(main(a[0] if a else wiki_from_env(), "--write" in sys.argv))
