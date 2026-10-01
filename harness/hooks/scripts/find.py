# -*- coding: utf-8 -*-
"""위키에서 문서를 찾는다.  파일을 열지 않고 머리말 한 줄로 고른다.

  python find.py {wiki} 낱말 [낱말...]  [--type overview|guideline|srs|fact] [--kind 배포]

**전문 검색이 아니다.** `description` · `제목` · `종류` 만 본다 —
본문까지 훑으면 관련도 높은 한 조각이 딸려 와서, 지침 네 줄 중 한 줄만 읽고
나머지 셋을 어기는 일이 생긴다. 고를 근거만 주고 여는 것은 사람이 정한다.
"""
import io, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def fm(p):
    try:
        t = io.open(p, encoding="utf-8", newline="").read(6000)
    except Exception:
        return {}
    m = re.match("^---" + chr(10) + "(.*?)" + chr(10) + "---", t, re.S)
    if not m:
        return {}
    d = {}
    for ln in m.group(1).split(chr(10)):
        mm = re.match(r"^([A-Za-z가-힣_]+):\s*(.*)$", ln)
        if mm:
            d[mm.group(1)] = mm.group(2).strip()
    return d


def main(wiki, words, want_type, want_kind):
    hits = []
    for root, dd, fs in os.walk(wiki):
        if ".git" in root:
            continue
        for f in fs:
            if not f.endswith(".md"):
                continue
            p = os.path.join(root, f)
            d = fm(p)
            if want_type and d.get("type") != want_type:
                continue
            if want_kind and d.get("종류") != want_kind:
                continue
            hay = (f + " " + d.get("description", "") + " " + d.get("종류", "")
                   + " " + d.get("system", "") + " " + d.get("aliases", ""))
            if words and not all(w.lower() in hay.lower() for w in words):
                continue
            hits.append((os.path.relpath(p, wiki), d))
    if not hits:
        print("없다. 낱말을 줄이거나 --type 을 빼고 다시 본다.")
        return 1
    print("%d건" % len(hits))
    for rel, d in sorted(hits):
        tag = d.get("종류") or d.get("type", "")
        st = d.get("강도", "")
        print("  %s%s" % (rel, ("   [%s%s]" % (tag, " " + st if st else "")) if tag else ""))
        ds = d.get("description", "")
        if ds:
            print("      " + ds[:110])
    return 0


def wiki_from_env():
    """위키 경로를 인자로 안 줬으면 VREINS_WIKI_ROOT 를 본다. 없으면 멈춘다 — 경로를 지어내지 않는다."""
    w = os.environ.get("VREINS_WIKI_ROOT")
    if not w or not os.path.isdir(w):
        sys.exit("위키 경로를 첫 인자로 주거나 VREINS_WIKI_ROOT 를 둔다")
    return w


if __name__ == "__main__":
    a = sys.argv[1:]
    wt = wk = None
    if "--type" in a:
        i = a.index("--type"); wt = a[i + 1]; del a[i:i + 2]
    if "--kind" in a:
        i = a.index("--kind"); wk = a[i + 1]; del a[i:i + 2]
    # 첫 인자가 경로처럼 보이면 위키 루트로 쓰고 낱말에서 뺀다.
    if a and (os.sep in a[0] or ":" in a[0]):
        wiki = a.pop(0)
    else:
        wiki = wiki_from_env()
    sys.exit(main(wiki, a, wt, wk))
