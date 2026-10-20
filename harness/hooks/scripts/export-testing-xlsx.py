# -*- coding: utf-8 -*-
"""05 테스트 산출물을 제출용 엑셀로 내보낸다.

  python export-testing-xlsx.py {05-testing-*.md} [-o {내보낼 경로}]

**마크다운이 정본이다.** 이 파일은 거기서 읽어 쓰기만 한다 — 엑셀을 고쳐도
문서는 안 바뀌고, 다음에 내보내면 덮인다. 고칠 것은 마크다운에서 고친다.

왜 외부 패키지를 안 쓰나 — xlsx 는 zip 안에 든 XML 이다. openpyxl 이 편하긴 하지만
그건 pip 로 받아야 하고, 이 플러그인은 받는 사람의 PC 를 고르지 않는다. 사내망에서
pip 가 막히는 날 「엑셀만 안 나오는」 고장이 되고, 그 사람은 제 문서를 의심한다.
표준 라이브러리로 끝낼 수 있는 일에 의존성을 늘리지 않는다.

시트 둘을 쓴다.

    단위 테스트 결과   현업 제출 양식 그대로. 9열
    개요              머리말 · 테스트 범위 · 미검증 항목 · 다음 단계로 넘기는 것

제출 양식에는 범위와 미검증 항목이 들어갈 자리가 없다. 그렇다고 버리면
**「안 본 것」이 사라진다** — 그 절은 빠뜨린 것과 해당 없는 것을 가르는 자리다.
"""
import io, os, re, sys, zipfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SHEET_MAIN = "단위 테스트 결과"
SHEET_INFO = "개요"

# 제출 양식의 열. **순서와 글자를 현업 파일에서 그대로 가져왔다.**
# 여기를 고치면 받는 쪽 양식과 어긋난다 — 고칠 일이 생기면 받은 파일부터 다시 본다.
COLUMNS = [
    ("No", 4.1),
    ("테스트 프로그램 ID", 17.6),
    ("테스트 프로그램명", 19.1),
    ("단위 Test ID", 11.9),
    ("단위 테스트 Case", 59.6),
    ("테스트 조건 및 기대 결과", 95.6),
    ("테스트 실제 결과", 15.4),
    ("결함 상태", 9.1),
    ("비고", 5.1),
]

# 마크다운 표의 머리글 → 우리가 쓰는 이름. **자리가 아니라 이름으로 찾는다.**
# 자리로 찾으면 열을 하나 끼워 넣은 날 전부 한 칸씩 밀리는데, 그게 조용히 밀린다.
HEADS = {
    "num":    ["#", "no", "번호"],
    "case":   ["테스트 case", "테스트 항목", "case", "항목"],
    "cond":   ["조건", "테스트 방법", "테스트 방법 (데이터)", "테스트 방법(데이터)"],
    "expect": ["기대", "기대 결과", "기대결과"],
    "actual": ["결과", "실제 결과", "테스트 실제 결과"],
    "note":   ["비고"],
    "kind":   ["구분"],
    "wrong":  ["무엇이 틀렸나", "무엇이 틀렸는가"],
    "fix":    ["조치"],
    "retest": ["재시험"],
}


SCREEN = re.compile(r"^[A-Z]{4}\d{3}[A-Z]\d{2}$")      # SPRG400E04
DROP = re.compile(r"^(\d{4,8}|SR|TS|SM|SR[\d-]+|TS[\d-]+)$", re.I)


def read(p):
    return io.open(p, encoding="utf-8", newline="").read()


def clean_cell(s):
    """표 칸을 제출용 글로 바꾼다.

    마크다운 기호와 <br> 은 **문서에서 읽기 좋으라고** 붙은 것이지 내용이 아니다.
    그대로 내보내면 현업이 받는 칸에 백틱과 별표가 박혀 나간다.
    """
    s = s or ""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", s)     # [[위키링크]]
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)              # [글](주소)
    s = s.replace("**", "").replace("`", "")
    return s.strip()


def title_of(folder):
    """세션 폴더 이름에서 제목만 꺼낸다.

      20260810_SR2607-03096_SPRG400E04_수출품Tag하단ShortBar프린팅  →  수출품Tag하단ShortBar프린팅
      2610-SR-임대임차입금일등록                                   →  임대임차입금일등록

    날짜·구분·SR번호·화면코드는 제목이 아니다. 폴더 이름을 통째로 내보내면
    「테스트 프로그램명」 칸에 경로가 들어간다.
    """
    for sep in ("_", "-"):
        parts = [p for p in folder.split(sep) if p]
        if len(parts) < 2:
            continue
        while parts and (DROP.match(parts[0]) or SCREEN.match(parts[0])):
            parts.pop(0)
        if parts:
            return sep.join(parts)
    return folder


def screen_code(fm, md_path):
    """화면코드. 머리말이 정본이고, 없으면 tags 와 폴더 이름에서 줍는다.

    양식은 머리말에 적게 하지만 **그 전에 쓴 문서가 이미 쌓여 있다.** 거기서는
    tags 에만 들어 있다 — 그걸 못 읽으면 옛 문서는 B·D 열이 빈 채로 나간다.
    """
    code = fm.get("화면코드", "")
    if isinstance(code, list):
        code = code[0] if code else ""
    code = (code or "").strip()
    if code:
        return code

    tags = fm.get("tags", "")
    if isinstance(tags, list):
        for t in tags:
            if SCREEN.match(t.strip()):
                return t.strip()

    for part in re.split(r"[_\-]", os.path.basename(os.path.dirname(os.path.abspath(md_path)))):
        if SCREEN.match(part):
            return part
    return ""


# ======================================================================
#  마크다운 읽기
# ======================================================================

def front_matter(text):
    """머리말을 읽는다. yaml 파서를 쓰지 않는다 — 우리 머리말은 한 줄 한 칸이고,
    파서를 들이면 이 스크립트가 pip 를 요구하게 된다."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return {}

    out = {}
    for line in m.group(1).split("\n"):
        line = line.split("#")[0].rstrip() if not line.strip().startswith("#") else ""
        kv = re.match(r"^([^:]+):\s*(.*)$", line)
        if not kv:
            continue
        key, val = kv.group(1).strip(), kv.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            val = [unquote(x) for x in val[1:-1].split(",") if x.strip()]
        else:
            val = unquote(val)
        out[key] = val
    return out


def unquote(s):
    """따옴표는 yaml 의 것이지 값이 아니다. 화면대역이 "610" 으로 나가면 안 된다."""
    s = (s or "").strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1].strip()
    return s


def sections(text):
    """## 로 끊는다. 제목 → 그 아래 본문.

    **첫 ## 앞의 본문도 한 절로 돌려준다.** 제목 없이 표부터 적은 문서가 실제로
    있다(`05-testing-SR2607-01292.md`). 그 앞부분을 버리면 케이스가 통째로
    사라지는데, 생성기는 「0 건」이라고만 말하고 사람은 제 문서를 의심한다.
    """
    body = re.sub(r"^---\r?\n.*?\r?\n---\r?\n", "", text, flags=re.S)
    out, title, buf = [], "", []
    for line in body.split("\n"):
        if line.startswith("## "):
            if "".join(buf).strip():
                out.append((title, "\n".join(buf)))
            title, buf = line[3:].strip(), []
        else:
            buf.append(line)
    if "".join(buf).strip():
        out.append((title, "\n".join(buf)))
    return out


def find_section(secs, *words):
    """제목에 그 글자가 든 절. 번호가 붙든 안 붙든 잡힌다 —
    실제 문서는 「2. 케이스와 결과」로도 「A. 자동 판정」으로도 쓴다."""
    for title, body in secs:
        low = title.lower()
        if any(w.lower() in low for w in words):
            return title, body
    return None, ""


def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def head_key(cell):
    c = re.sub(r"[*`]", "", cell).strip().lower()
    for key, names in HEADS.items():
        if c in names:
            return key
    return None


def tables(body):
    """본문 안의 표를 전부 읽는다. 앞선 ### 소제목을 그 표의 이름으로 붙인다.

    반환: [(소제목, [{열이름: 값}, …]), …]"""
    out, sub, lines = [], "", body.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("### "):
            sub = line[4:].strip()
            i += 1
            continue

        is_table = ("|" in line and i + 1 < len(lines)
                    and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]+$", lines[i + 1]))
        if not is_table:
            i += 1
            continue

        keys = [head_key(c) for c in split_row(line)]
        i += 2
        rows = []
        while i < len(lines) and "|" in lines[i]:
            cells = split_row(lines[i])
            row = {}
            for k, v in zip(keys, cells):
                if k:
                    row[k] = v
            if any(v for v in row.values()):
                rows.append(row)
            i += 1
        if rows:
            out.append((sub, rows))
    return out


def plain(body):
    """절 본문을 사람이 읽을 글로 돌려준다. 표와 빈 줄은 버린다."""
    keep = []
    for line in body.split("\n"):
        s = line.strip()
        if not s or s.startswith("|") or s.startswith("<!--"):
            continue
        keep.append(re.sub(r"[*`]", "", s))
    return "\n".join(keep)


# ======================================================================
#  xlsx 쓰기 — zip 안의 XML 이다
# ======================================================================

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NSR = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NSPKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "application/vnd.openxmlformats-officedocument.spreadsheetml"


def esc(s):
    s = "" if s is None else str(s)
    # 엑셀이 제어문자를 못 받는다. 줄바꿈·탭만 남긴다.
    s = "".join(ch for ch in s if ch in "\n\t" or ord(ch) >= 32)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def col_name(n):
    name = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        name = chr(65 + r) + name
    return name


def cell(ref, value, style):
    if value is None or value == "":
        return '<c r="%s" s="%d"/>' % (ref, style)
    return ('<c r="%s" s="%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
            % (ref, style, esc(value)))


def sheet_xml(rows, widths, freeze_header):
    """rows: [[(글자, 스타일), …], …]"""
    cols = ""
    if widths:
        cols = "<cols>" + "".join(
            '<col min="%d" max="%d" width="%.1f" customWidth="1"/>' % (i + 1, i + 1, w)
            for i, w in enumerate(widths)) + "</cols>"

    pane = ""
    if freeze_header:
        pane = ('<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
                '<selection pane="bottomLeft"/>')

    body = []
    for r, cells in enumerate(rows, start=1):
        parts = [cell("%s%d" % (col_name(c), r), v, s) for c, (v, s) in enumerate(cells, start=1)]
        body.append('<row r="%d">%s</row>' % (r, "".join(parts)))

    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="%s">'
            '<sheetViews><sheetView workbookViewId="0">%s</sheetView></sheetViews>'
            '<sheetFormatPr defaultRowHeight="15"/>'
            '%s<sheetData>%s</sheetData>'
            '</worksheet>' % (NS, pane, cols, "".join(body)))


# 스타일 넷. 0 기본 · 1 머리글 · 2 본문 · 3 본문 가운데
STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<styleSheet xmlns="%s">'
          '<fonts count="2">'
          '<font><sz val="11"/><name val="맑은 고딕"/></font>'
          '<font><b/><sz val="11"/><name val="맑은 고딕"/></font>'
          '</fonts>'
          '<fills count="3">'
          '<fill><patternFill patternType="none"/></fill>'
          '<fill><patternFill patternType="gray125"/></fill>'
          '<fill><patternFill patternType="solid">'
          '<fgColor rgb="FFDCE6F1"/><bgColor indexed="64"/></patternFill></fill>'
          '</fills>'
          '<borders count="2">'
          '<border><left/><right/><top/><bottom/><diagonal/></border>'
          '<border><left style="thin"/><right style="thin"/>'
          '<top style="thin"/><bottom style="thin"/><diagonal/></border>'
          '</borders>'
          '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
          '<cellXfs count="4">'
          '<xf xfId="0" numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
          '<xf xfId="0" numFmtId="0" fontId="1" fillId="2" borderId="1" applyFont="1"'
          ' applyFill="1" applyBorder="1" applyAlignment="1">'
          '<alignment horizontal="center" vertical="center" wrapText="1"/></xf>'
          '<xf xfId="0" numFmtId="0" fontId="0" fillId="0" borderId="1" applyBorder="1"'
          ' applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
          '<xf xfId="0" numFmtId="0" fontId="0" fillId="0" borderId="1" applyBorder="1"'
          ' applyAlignment="1">'
          '<alignment horizontal="center" vertical="top" wrapText="1"/></xf>'
          '</cellXfs>'
          # cellStyles 는 cellXfs **뒤**다. 스키마가 순서를 정해 두었고, 어기면
          # 엑셀이 「복구할 수 없는 내용」이라며 파일을 거절한다.
          '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
          '</styleSheet>' % NS)


def write_xlsx(path, sheets):
    """sheets: [(이름, rows, widths, 틀고정), …]"""
    n = len(sheets)

    types = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/>'
             '<Override PartName="/xl/workbook.xml" ContentType="%s.sheet.main+xml"/>'
             '<Override PartName="/xl/styles.xml" ContentType="%s.styles+xml"/>' % (CT, CT)]
    for i in range(n):
        types.append('<Override PartName="/xl/worksheets/sheet%d.xml" '
                     'ContentType="%s.worksheet+xml"/>' % (i + 1, CT))
    types.append("</Types>")

    sheet_tags = "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (esc(s[0]), i + 1, i + 1)
                         for i, s in enumerate(sheets))
    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="%s" xmlns:r="%s"><sheets>%s</sheets></workbook>'
                % (NS, NSR, sheet_tags))

    rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="%s">' % NSPKG]
    for i in range(n):
        rels.append('<Relationship Id="rId%d" Type="%s/worksheet" '
                    'Target="worksheets/sheet%d.xml"/>' % (i + 1, NSR, i + 1))
    rels.append('<Relationship Id="rId%d" Type="%s/styles" Target="styles.xml"/>' % (n + 1, NSR))
    rels.append("</Relationships>")

    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="%s"><Relationship Id="rId1" '
                 'Type="%s/officeDocument" Target="xl/workbook.xml"/></Relationships>'
                 % (NSPKG, NSR))

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "".join(types))
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rels))
        z.writestr("xl/styles.xml", STYLES)
        for i, (_, rows, widths, freeze) in enumerate(sheets):
            z.writestr("xl/worksheets/sheet%d.xml" % (i + 1), sheet_xml(rows, widths, freeze))


# ======================================================================
#  내보내기
# ======================================================================

def build(md_path):
    text = read(md_path)
    fm = front_matter(text)
    secs = sections(text)

    sr = fm.get("id", "") or ""
    codes = screen_code(fm, md_path)
    # 「테스트 프로그램명」은 머리말 화면명이 있으면 그것, 없으면 세션 폴더가 댄다.
    folder = os.path.basename(os.path.dirname(os.path.abspath(md_path)))
    name = (fm.get("화면명", "") or "").strip() or title_of(folder)

    # --- 3. 실패와 조치를 먼저 읽는다. 케이스 번호로 이어 붙일 것이다 ---------
    defects = {}
    _, fail_body = find_section(secs, "실패와 조치", "실패")
    for _sub, rows in tables(fail_body):
        for row in rows:
            key = re.sub(r"\D", "", row.get("num", ""))
            if not key:
                continue
            bits = [row.get("fix", ""), row.get("retest", "")]
            defects[key] = (row.get("kind", "").strip(),
                            " / ".join(b for b in bits if b))

    # --- 2. 케이스와 결과 ----------------------------------------------------
    head = [(c, 1) for c, _ in COLUMNS]
    rows_out = [head]

    _, case_body = find_section(secs, "케이스", "케이스와 결과")
    if not case_body:
        # 절 제목이 양식과 다른 문서가 실제로 있다. 그때는 전체에서 표를 긁는다 —
        # 못 찾았다고 빈 파일을 내놓으면 사람은 자기가 안 쓴 줄 안다.
        case_body = "\n".join(b for t, b in secs
                              if "실패" not in t and "미검증" not in t)

    seq = 0
    for sub, rows in tables(case_body):
        for row in rows:
            if "case" not in row and "cond" not in row:
                continue
            seq += 1
            num = re.sub(r"\D", "", row.get("num", "")) or str(seq)

            cond = clean_cell(row.get("cond", ""))
            expect = clean_cell(row.get("expect", ""))
            # 제출 양식은 조건과 기대가 한 칸이다. 문서에서는 갈라 쓰고 여기서 합친다 —
            # 합쳐 두면 되돌릴 수 없고, 가른 쪽이 읽기도 낫다.
            both = "\n".join(x for x in [cond, ("기대: " + expect) if expect else ""] if x)

            kind, fix = defects.get(num, ("", ""))
            note = clean_cell(row.get("note", ""))
            if sub:
                note = (clean_cell(sub) + (" / " + note if note else ""))
            if fix:
                note = (note + " / " if note else "") + clean_cell(fix)

            rows_out.append([
                (num, 3),
                (codes, 3),
                (name, 2),
                ("%s_%03d" % (codes, int(num)) if codes and num.isdigit() else "", 3),
                (clean_cell(row.get("case", "")), 2),
                (both, 2),
                (clean_cell(row.get("actual", "")), 3),
                (clean_cell(kind), 3),
                (note, 2),
            ])

    # --- 개요 시트 -----------------------------------------------------------
    info = [[("항목", 1), ("내용", 1)]]
    for key in ["id", "system", "techbase", "화면코드", "화면대역", "description", "updated"]:
        val = fm.get(key, "")
        if isinstance(val, list):
            val = ", ".join(val)
        if val:
            info.append([(key, 3), (val, 2)])

    for want in ["테스트 범위", "미검증", "다음 단계"]:
        title, body = find_section(secs, want)
        if title:
            info.append([(title, 3), (plain(body), 2)])

    return sr, [(SHEET_MAIN, rows_out, [w for _, w in COLUMNS], True),
                (SHEET_INFO, info, [22.0, 100.0], True)]


def main(argv):
    if not argv:
        print(__doc__)
        return 2

    md_path = argv[0]
    out = None
    if "-o" in argv:
        out = argv[argv.index("-o") + 1]

    if not os.path.isfile(md_path):
        print("[오류] 그런 파일이 없다 — %s" % md_path)
        return 1

    sr, sheets = build(md_path)
    cases = len(sheets[0][1]) - 1
    if cases == 0:
        # 빈 파일을 조용히 내놓지 않는다. 사람은 제출하고 나서 안다.
        print("[오류] 케이스를 한 건도 못 읽었다 — 2 절의 표 머리글을 확인한다")
        print("       아는 머리글: # · 테스트 Case · 조건 · 기대 · 결과 · 비고")
        return 1

    if not out:
        base = "단위테스트결과서_%s_v1.0.xlsx" % (sr or "결과")
        out = os.path.join(os.path.dirname(os.path.abspath(md_path)), base)

    write_xlsx(out, sheets)
    print("[완료] 케이스 %d 건 → %s" % (cases, out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
