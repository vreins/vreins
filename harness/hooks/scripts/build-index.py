#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wiki/index.md 를 짓는다.  사람이 보는 표지다 — 손으로 고치지 않는다.

    python build-index.py {위키루트}

정본은 각 overview.md 의 frontmatter 다 (lifecycle · description · owner · related).
이 파일은 그것을 모아 찍는다. 다시 돌리면 덮어쓴다.

SR 목록은 넣지 않는다 — `ls {유형}/{시스템}/{연도}/` 가 준다.
폴더명에 날짜 92% · SR번호 67% · 제목 100% 가 들어 있다(2026-09-21 실측).

왜 파이썬인가 — 훅은 PowerShell 이지만 이건 훅이 아니라 도구다.
사람이 부르거나 커밋 훅이 부른다. PS 로 다시 쓸 이유가 생기면 그때 옮긴다.
"""

import io
import os
import re
import sys

TYPES = ["MES", "LEVEL2", "WEB", "APP"]
NL = chr(10)

SR_PATH = re.compile(r"^(APP|MES|LEVEL2|WEB)/([A-Za-z0-9_]+)/(\d{4})/([^/]+)/readme(?:-[^/]*)?\.md$")
SRID = re.compile(r"(SR\d{4}-\d{3,5})")
SEC = re.compile(r"^## \d+\.")


# ---------------------------------------------------------------- frontmatter

def frontmatter(path):
    """--- ... --- 사이를 아주 얕게 읽는다. 스칼라와 `related:` 블록만."""
    txt = io.open(path, encoding="utf-8").read()
    if not txt.startswith("---"):
        return {}, txt
    end = txt.find(NL + "---", 3)
    if end < 0:
        return {}, txt
    head = txt[3:end]
    body = txt[end + 4:]
    fm = {}
    cur = None
    for line in head.split(NL):
        if not line.strip():
            continue
        if line.startswith("  ") or line.startswith("\t"):
            if cur == "related":
                fm.setdefault("related", []).append(line)
            continue
        m = re.match(r"^([A-Za-z_가-힣0-9]+):\s*(.*)$", line)
        if not m:
            continue
        cur = m.group(1)
        if cur == "related":
            fm.setdefault("related", [])
        else:
            fm[cur] = m.group(2).strip()
    return fm, body


def parse_related(lines):
    """`related:` 밑 들여쓴 줄을 [{system, rel, why}] 로."""
    out = []
    for line in lines:
        s = line.strip()
        if s.startswith("- "):
            out.append({})
            s = s[2:]
        if not out:
            continue
        m = re.match(r"^([a-z]+):\s*(.*)$", s)
        if m:
            out[-1][m.group(1)] = m.group(2).strip()
    return [r for r in out if r.get("system")]


# ---------------------------------------------------------------- 세기

def unwritten_sections(body):
    """`## N.` 절 가운데 <!-- UNWRITTEN --> 을 품은 절의 수와 전체 절 수."""
    total = 0
    hit = 0
    inside = False
    marked = False
    for line in body.split(NL):
        if SEC.match(line):
            if inside and marked:
                hit += 1
            inside = True
            marked = False
            total += 1
        elif inside and "UNWRITTEN" in line:
            marked = True
    if inside and marked:
        hit += 1
    return hit, total


def sr_label(folder):
    """폴더 이름에서 사람이 고를 수 있는 짧은 이름을 뽑는다."""
    m = SRID.search(folder)
    date = ""
    d = re.match(r"^(\d{4}-\d{2}-\d{2})[-_]", folder)
    if d:
        date = d.group(1)
    else:
        d = re.match(r"^(\d{8})[-_]", folder)
        if d:
            date = d.group(1)
        else:
            d = re.match(r"^(\d{4})[-_]", folder)
            if d:
                date = d.group(1)
    if m:
        return (date + " " + m.group(1)).strip()
    rest = folder
    if date:
        rest = folder[len(date) + 1:]
    return (date + " " + rest).strip()


def sr_sortkey(folder):
    d = re.match(r"^(\d{4})-(\d{2})-(\d{2})[-_]", folder)
    if d:
        return d.group(1) + d.group(2) + d.group(3)
    d = re.match(r"^(\d{8})[-_]", folder)
    if d:
        return d.group(1)
    d = re.match(r"^(\d{2})(\d{2})[-_]", folder)
    if d:
        return "20" + d.group(1) + d.group(2) + "00"
    return "00000000"


def folder_title(folder):
    """폴더 이름에서 날짜·SR 번호·TS 를 뺀 제목 부분."""
    rest = re.sub(r"^\d{4}-\d{2}-\d{2}[-_]", "", folder)
    rest = re.sub(r"^\d{8}[-_]", "", rest)
    rest = re.sub(r"^\d{4}[-_]", "", rest)
    rest = re.sub(r"^SR\d{4}-\d{3,5}[-_]", "", rest)
    rest = re.sub(r"^TS[-_]", "", rest)
    return rest


def trim_desc(desc, label, folder):
    """description 을 목차 한 줄에 맞게 다듬는다.

    - 머리의 SR 번호가 라벨과 겹치면 뺀다
    - 아직 제목이 안 적힌 껍데기(`01 · 분석 · 산출물 …`)는 폴더 제목으로 갈음한다
    """
    m = re.match(r"^\d{2} · [^·]+ · (산출물.*)$", desc)
    if m:
        return folder_title(folder) + " · " + m.group(1)
    m = SRID.match(desc)
    if m and m.group(1) in label:
        return desc[m.end():].lstrip(" —·-")
    return desc


# ---------------------------------------------------------------- 모으기

def collect(root):
    systems = {}
    for typ in TYPES:
        tdir = os.path.join(root, typ)
        if not os.path.isdir(tdir):
            continue
        for name in sorted(os.listdir(tdir)):
            ov = os.path.join(tdir, name, "overview.md")
            if not os.path.isfile(ov):
                continue
            fm, body = frontmatter(ov)
            hit, total = unwritten_sections(body)
            systems[typ + "/" + name] = {
                "type": typ,
                "code": name,
                "lifecycle": fm.get("lifecycle", ""),
                "description": fm.get("description", ""),
                "related": parse_related(fm.get("related", [])),
                "unwritten": hit,
                "sections": total,
                "srs": [],
            }
    # SR
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath.replace("\\", "/").split("/"):
            continue
        names = [f for f in filenames
                 if f == "readme.md" or (f.startswith("readme-") and f.endswith(".md"))]
        if not names:
            continue
        name = sorted(names)[0]
        rel = os.path.join(dirpath, name).replace("\\", "/")[len(root) + 1:]
        m = SR_PATH.match(rel)
        if not m:
            continue
        key = m.group(1) + "/" + m.group(2)
        if key not in systems:
            continue
        fm, _ = frontmatter(os.path.join(dirpath, name))
        folder = m.group(4)
        label = sr_label(folder)
        systems[key]["srs"].append({
            "path": rel,
            "label": label,
            "desc": trim_desc(fm.get("description", ""), label, folder),
            "sort": sr_sortkey(folder) + folder,
        })
    for s in systems.values():
        s["srs"].sort(key=lambda x: x["sort"], reverse=True)
    # related 역방향
    for key, s in systems.items():
        for r in s["related"]:
            for k2, s2 in systems.items():
                if s2["code"] == r["system"]:
                    s2.setdefault("incoming", []).append(s["code"])
    return systems


# ---------------------------------------------------------------- 쓰기

def system_line(key, s):
    bits = []
    if s["srs"]:
        bits.append("이력 %d건" % len(s["srs"]))
    if s["unwritten"]:
        bits.append("%d절 중 %d절 미작성" % (s["sections"], s["unwritten"]))
    if s["related"]:
        bits.append("→ " + "·".join(r["system"] for r in s["related"]))
    inc = sorted(set(s.get("incoming", [])))
    if inc:
        bits.append("← " + "·".join(inc))
    line = "- [%s](%s/overview.md) — %s" % (key, key, s["description"])
    if bits:
        line += "  ·  " + " · ".join(bits)
    return line


# ─────────────────────────────────────────────────────────────────────
# SR 을 목차에 넣을까 — 안 넣는다
#
#   이 파일은 사람이 보는 표지다. SR 을 찾는 일은 `/find` 가 한다.
#   목차에 SR 을 또 적으면 같은 사실이 두 벌이 되고, 한쪽이 낡는다 —
#   낡는 쪽은 언제나 손으로 안 짓는 쪽이 아니라 아무도 안 보는 쪽이다.
#
#   폴더를 훑고 싶으면 `ls {유형}/{시스템}/{연도}/` 로 족하다.
#   폴더명에 날짜·SR번호·제목이 다 들어 있어서 목록을 따로 만들 필요가 없다.
#
#   시스템 줄의 「이력 N건」은 남긴다 — 규모를 보여 주는 숫자이지 목록이 아니다.
#
#   (크기 때문이 아니다. 2026-09-21 실측으로 61건을 넣으면 17,071자였고
#    상한 8,000자를 넘기긴 했지만, 상한을 늘려도 이 결론은 안 바뀐다.)
WITH_SR = False
# ─────────────────────────────────────────────────────────────────────

def sr_line(sr):
    return "    - [%s](%s) — %s" % (sr["label"], sr["path"], sr["desc"])


def build(root):
    systems = collect(root)
    prod = {k: v for k, v in systems.items() if v["lifecycle"] == "production"}
    skel = {k: v for k, v in systems.items() if v["lifecycle"] == "skeleton"}
    other = {k: v for k, v in systems.items() if v["lifecycle"] not in ("production", "skeleton")}

    md = []
    w = md.append

    n_md = 0
    for dirpath, dirnames, filenames in os.walk(root):
        if ".git" in dirpath.replace("\\", "/").split("/"):
            continue
        n_md += sum(1 for f in filenames if f.endswith(".md"))
    n_sr = sum(len(v["srs"]) for v in systems.values())

    w("---")
    w("type: fact")
    w("techbase: []")
    w("description: 위키 전체 목차 — 시스템마다 한 줄. 좌표 없는 질문은 여기서 고른다")
    w("updated: 2026-09-21")
    w("---")
    w("")
    w("# vReins 위키 — 목차")
    w("")
    w("> **이 파일은 기계가 짓는다.** 손으로 고치지 않는다 —")
    w("> 각 `overview.md` 의 frontmatter(`lifecycle`·`description`·`related`)가 정본이다.")
    w("> 구조와 규약은 [readme.md](readme.md).")
    w("> 위키 자체에 무슨 일이 있었는지는 **git 로그**가 갖는다 — `log.md` 는 2026-09-21 에 없앴다. git 과 두 벌이었다.")
    w("")
    w("**사람이 지형을 볼 때 보는 표지다.** 도구 없이 웹에서 열어도 보인다 —")
    w("무엇이 있고 무엇이 없는지, 어느 시스템이 어느 시스템과 엮이는지가 한 화면에 들어온다.")
    w("")
    w("**LLM 이 SR 을 찾을 때는 `/find` 를 쓴다.** 이 파일에 SR 목록이 없는 이유다.")
    w("")
    w("```")
    w("시스템을 정한다        여기서 한 줄 요약을 보고 고른다")
    w("들어간다              {유형}/{시스템}/overview.md")
    w("폴더를 훑는다          ls {유형}/{시스템}/{연도}/")
    w("                      폴더명에 날짜·SR번호·제목이 다 들어 있다")
    w("SR 을 찾는다           /find")
    w("```")
    w("")
    w("---")
    w("")
    w("## 우리가 맡은 시스템 — %d개" % len(prod))
    w("")
    w("레지스트리에 등록돼 있다. 줄 끝 「이력 N건」은 그 시스템에 쌓인 작업 수다 — 합 %d건." % n_sr)
    w("")
    for typ in TYPES:
        keys = [k for k in sorted(prod) if prod[k]["type"] == typ]
        if not keys:
            continue
        w("### " + typ)
        w("")
        for k in keys:
            w(system_line(k, prod[k]))
            if WITH_SR:
                for sr in prod[k]["srs"]:
                    w(sr_line(sr))
        w("")
    w("---")
    w("")
    w("## 뼈대만 있는 것 — %d개" % len(skel))
    w("")
    w("**우리 담당이 아니다.** 실재한다는 것과 규모만 적어 뒀다 — 없는 줄 모르는 것과는 다르다.")
    w("")
    for typ in TYPES:
        keys = [k for k in sorted(skel) if skel[k]["type"] == typ]
        if not keys:
            continue
        w("### " + typ)
        w("")
        for k in keys:
            w(system_line(k, skel[k]))
        w("")
    if other:
        w("### lifecycle 이 없다 — 고쳐야 한다")
        w("")
        for k in sorted(other):
            w(system_line(k, other[k]))
        w("")
    w("---")
    w("")

    edges = []
    for k in sorted(systems):
        for r in systems[k]["related"]:
            edges.append((systems[k]["code"], r.get("rel", ""), r["system"], r.get("why", "")))
    w("## 공정을 가로지르는 위험 — %d쌍" % len(edges))
    w("")
    w("`overview.md` 의 `related:` 에서 **기계가 모은 것**이다. 한쪽만 적으면 반대쪽은 여기서 나온다.")
    w("")
    w("| 가리키는 쪽 | 종류 | 가리켜지는 쪽 | 무엇 |")
    w("|---|---|---|---|")
    for a, rel, b, why in edges:
        w("| `%s` | %s | `%s` | %s |" % (a, rel, b, why))
    w("")
    w("---")
    w("")
    w("## 시스템에 안 붙는 것")
    w("")
    loose = [
        ("glossary.md", "낱말"),
        ("공정코드.md", "공정코드 62개 전수"),
        ("process/readme.md", "공정 묶음"),
        ("_inbox/readme.md", "아직 위키가 안 된 것"),
    ]
    for path, what in loose:
        if os.path.isfile(os.path.join(root, path)):
            w("- [%s](%s) — %s" % (path, path, what))
    w("")
    for typ in TYPES:
        shelf = []
        for sub in ("knowledge", "rules", "closing", "_manual"):
            p = typ + "/" + sub + "/readme.md"
            if os.path.isfile(os.path.join(root, p)):
                shelf.append("[%s/](%s)" % (sub, p))
        if shelf:
            w("- **%s** — %s" % (typ, " · ".join(shelf)))
    w("")
    w("---")
    w("")
    w("```")
    w("문서    %-9d overview %d · 이력 %d · 그 밖 %d" % (n_md, len(systems), n_sr, n_md - len(systems) - n_sr))
    w("공정코드  62개 전수 — 공정코드.md")
    w("```")
    w("")

    out = os.path.join(root, "index.md")
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(NL.join(md))
    print("wrote %s  (%d lines)" % (out, len(md)))
    print("  production %d · skeleton %d · 이력 %d · 문서 %d" % (len(prod), len(skel), n_sr, n_md))


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "C:/gitroot/260915/wiki")
