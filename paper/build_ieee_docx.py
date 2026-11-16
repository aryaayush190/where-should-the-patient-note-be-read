"""Build the TELMED 2027 submission as a Word file in the official IEEE conference template (US Letter).

    python paper/build_ieee_docx.py      (system Python with python-docx)

Inputs
  paper/ieee_template_src/conference-template-letter_transitional.docx  IEEE template (re-saved by Word
      from the official Strict-OOXML download so python-docx can open it; styles untouched)
  paper/generated/numbers.tex   every result number ({m:name} below), from experiments/paper_numbers.py
  paper/figures/*.png           600-dpi figures from paper/figures/make_figures.py
Output
  paper/TELMED2027_submission.docx   (convert to PDF with Word; see paper/README or the session notes)

Text markup: {m:macro} = generated number, {c:key[,key]} = citation (numbered in order of first use),
*italic*, **bold**.
"""
import copy
import os
import re
from pathlib import Path

import sys

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
TEMPLATE = HERE / "ieee_template_src" / "conference-template-letter_transitional.docx"
OUT = HERE / (sys.argv[1] if len(sys.argv) > 1 else "TELMED2027_submission.docx")
FIG = HERE / "figures"

# ───────────────────────────────────────────── numbers
MAC = {}
for line in (HERE / "generated" / "numbers.tex").read_text(encoding="utf-8").splitlines():
    m = re.match(r"\\newcommand\{\\([A-Za-z]+)\}\{(.*)\}\s*$", line)
    if m:
        MAC[m.group(1)] = m.group(2)
SUP = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def num(name):
    v = MAC[name]
    if "pending" in v:
        if os.environ.get("ALLOW_PENDING"):   # layout preview only; a final build must have every number
            return "[pending]"
        raise SystemExit(f"macro {name} is pending")
    v = v.replace("\\%", "%")
    v = re.sub(r"\\times\s*10\^\{(-?\d+)\}", lambda mm: "×10" + mm.group(1).translate(SUP), v)
    v = v.replace("$", "")
    if v.startswith("-"):
        v = "−" + v[1:]
    return v


# ───────────────────────────────────────────── references (IEEE style), 15 entries
REFS = {
    "oliver": "H. Oliver et al., “Personal data ecosystems in decentralised clinical trials,” in *Proc. IEEE Int. "
              "Conf. Pervasive Comput. Commun. Workshops (PerCom Workshops), TELMED*, 2026.",
    "jin": "Q. Jin et al., “Matching patients to clinical trials with large language models,” *Nat. Commun.*, "
           "vol. 15, Art. no. 9074, 2024, doi: 10.1038/s41467-024-53081-z.",
    "abdallah": "M. Abdallah et al., “TrialMatchAI: An end-to-end AI-powered clinical trial recommendation system "
                "to streamline patient-to-trial matching,” *Nat. Commun.*, vol. 17, Art. no. 4472, 2026, doi: 10.1038/s41467-026-70509-w.",
    "indicon": "A. Arya et al., “Hard structural vetoes under unseen trial shift: An empirical study of LLM-based "
               "clinical trial matching,” in *Proc. IEEE INDICON*, 2026, accepted with major revision.",
    "dpdp": "Government of India, “The Digital Personal Data Protection Act, 2023 (No. 22 of 2023),” 2023.",
    "magnini": "M. Magnini, G. Ciatto, A. E. Kuru, C. Sirocchi, and S. Montagna, “Neuro-symbolic AI for supporting "
               "chronic disease diagnosis and monitoring,” in *Proc. IEEE PerCom Workshops (TELMED)*, 2025, "
               "pp. 446–451.",
    "yuan": "C. Yuan et al., “Criteria2Query: A natural language interface to clinical databases for cohort "
            "definition,” *J. Amer. Med. Inform. Assoc.*, vol. 26, no. 4, pp. 294–305, 2019, doi: 10.1093/jamia/ocy178.",
    "prism": "S. Gupta et al., “PRISM: Patient records interpretation for semantic clinical trial matching system "
             "using large language models,” *npj Digit. Med.*, vol. 7, Art. no. 305, 2024, doi: 10.1038/s41746-024-01274-7.",
    "qu": "B. Qu, L. Ranaldi, X. Wang, and M. Valentino, “Neurosymbolic clinical trial matching via LLM-driven "
          "abduction and logical verification,” arXiv:2606.20895, 2026.",
    "zhan": "J. Zhan, H. Shen, Z. Lin, and T. He, “PRISM: Privacy-aware routing for adaptive cloud–edge LLM "
            "inference via semantic sketch collaboration,” arXiv:2511.22788, 2025.",
    "montagna": "S. Montagna et al., “LLM-based solutions for healthcare chatbots: A comparative analysis,” in "
                "*Proc. IEEE PerCom Workshops (TELMED)*, 2024, pp. 346–351.",
    "aguzzi": "G. Aguzzi, S. Montagna, and S. Ferretti, “Privacy leakage in small agentic healthcare models: An "
              "empirical analysis,” in *Proc. IEEE PerCom Workshops (TELMED)*, 2026.",
    "gptoss": "OpenAI, “gpt-oss-120b & gpt-oss-20b model card,” arXiv:2508.10925, 2025.",
    "qwen38": "Qwen Team, “Qwen3.8-27B,” open-weights model card, Hugging Face (Qwen/Qwen3.8-27B), Apache-2.0, 2026.",
    "qwen3": "A. Yang et al., “Qwen3 technical report,” arXiv:2505.09388, 2025.",
}

# ───────────────────────────────────────────── authors
AUTHORS = [
    ("Ayush Arya", "Applied Cognitive Science Lab", "Indian Institute of Technology Mandi", "Himachal Pradesh, India",
     "aryaayush190@gmail.com"),
    ("Neha Kriti", "Applied Cognitive Science Lab", "Indian Institute of Technology Mandi", "Himachal Pradesh, India",
     "d24045@students.iitmandi.ac.in"),
    ("Harsha Kulkarni", "University Institute of Technology", "Himachal Pradesh University", "Himachal Pradesh, India",
     "kulkarniharsha191205@gmail.com"),
    ("Sarthak Srivastava", "Applied Cognitive Science Lab", "Indian Institute of Technology Mandi",
     "Himachal Pradesh, India", "sarthaksrivastava1999@gmail.com"),
    ("Shruti Kaushik", "Syneos Health", None, "India", "shrutikaushik15@gmail.com"),
    ("Varun Dutt (corresponding author)", "Applied Cognitive Science Lab", "Indian Institute of Technology Mandi",
     "Himachal Pradesh, India", "varun@iitmandi.ac.in"),
]

from paper_content import ABSTRACT, BODY, BOXES, KEYWORDS, REPO_URL, TABLES, TITLE  # noqa: E402

# ───────────────────────────────────────────── citation numbering (order of first use)
ORDER = []


def collect_cites(text):
    for m in re.finditer(r"\{c:([^}]*)\}", text):
        for k in m.group(1).split(","):
            k = k.strip()
            if k not in REFS:
                raise SystemExit(f"unknown citation key {k}")
            if k not in ORDER:
                ORDER.append(k)


for kind, payload in BODY:
    if kind in ("p", "ack"):
        collect_cites(payload)
    elif kind == "bullets":
        for b in payload:
            collect_cites(b)
    elif kind == "box":
        for b in BOXES[payload]["items"]:
            collect_cites(b)
missing = set(REFS) - set(ORDER)
if missing:
    raise SystemExit(f"references never cited: {missing}")


def neg(name):
    """Sign-flipped number, so every difference can be written as 'system minus reference'."""
    v = MAC[name].replace("\\%", "")
    x = -float(v)
    dec = len(v.split(".")[1]) if "." in v else 0
    out = f"{abs(x):.{dec}f}"
    if x > 0 and float(out) != 0:
        return "+" + out
    if x < 0 and float(out) != 0:
        return "−" + out
    return out


def resolve(text):
    text = re.sub(r"\{n:([A-Za-z]+)\}", lambda m: neg(m.group(1)), text)
    text = re.sub(r"\{m:([A-Za-z]+)\}", lambda m: num(m.group(1)), text)
    text = re.sub(r"\{c:([^}]*)\}", lambda m: ", ".join(f"[{ORDER.index(k.strip()) + 1}]"
                                                        for k in m.group(1).split(",")), text)
    return text


# ───────────────────────────────────────────── docx helpers
SECT = ('<w:sectPr {ns}>{typ}<w:pgSz w:w="12240" w:h="15840" w:code="1"/>'
        '<w:pgMar w:top="1080" w:right="893" w:bottom="1440" w:left="893" w:header="720" w:footer="720" w:gutter="0"/>'
        '<w:cols {cols}/><w:docGrid w:linePitch="360"/></w:sectPr>')


def sectpr(cols, continuous=True):
    c = f'w:num="{cols}" w:space="{360 if cols == 2 else 216}"' if cols > 1 else 'w:space="720"'
    return parse_xml(SECT.format(ns=nsdecls("w"), typ='<w:type w:val="continuous"/>' if continuous else "", cols=c))


def end_section(par, cols, continuous=True):
    par._p.get_or_add_pPr().append(sectpr(cols, continuous))


def add_runs(par, text, size=None, base_italic=None, base_bold=None):
    """**bold**, *italic* markup -> runs."""
    for tok in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text):
        if not tok:
            continue
        bold, ital = base_bold, base_italic
        if tok.startswith("**"):
            tok, bold = tok[2:-2], True
        elif tok.startswith("*"):
            tok, ital = tok[1:-1], True
        r = par.add_run(tok)
        if bold is not None:
            r.bold = bold
        if ital is not None:
            r.italic = ital
        if size:
            r.font.size = Pt(size)
    return par


def set_cell(cell, text, width_in, bold=False, align="center", size=8):
    cell.width = Inches(width_in)
    p = cell.paragraphs[0]
    p.style = DOC.styles["table copy"]
    p.alignment = {"center": WD_ALIGN_PARAGRAPH.CENTER, "left": WD_ALIGN_PARAGRAPH.LEFT}[align]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    for k, line in enumerate(text.split("\n")):
        if k:
            p.add_run().add_break()
        add_runs(p, line, size=size, base_bold=bold if bold else None)
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(parse_xml(f'<w:tcMar {nsdecls("w")}><w:left w:w="22" w:type="dxa"/><w:right w:w="22" w:type="dxa"/>'
                          f'</w:tcMar>'))


def border(cell, side, sz=6):
    tcPr = cell._tc.get_or_add_tcPr()
    b = tcPr.find(qn("w:tcBorders"))
    if b is None:
        b = parse_xml(f'<w:tcBorders {nsdecls("w")}/>')
        mar = tcPr.find(qn("w:tcMar"))  # schema order: tcW, ..., tcBorders, shd, ..., tcMar
        if mar is not None:
            mar.addprevious(b)
        else:
            tcPr.append(b)
    b.append(parse_xml(f'<w:{side} {nsdecls("w")} w:val="single" w:sz="{sz}" w:space="0" w:color="000000"/>'))


def add_table(key):
    t = TABLES[key]
    cap = DOC.add_paragraph(style="table head")
    cap.add_run(t["caption"])
    cap.paragraph_format.keep_with_next = True
    ncol = len(t["header"])
    tbl = DOC.add_table(rows=1 + len(t["rows"]), cols=ncol)
    tbl.alignment = 1  # centre
    tbl.autofit = False
    tblPr = tbl._tbl.tblPr
    lay = parse_xml(f'<w:tblLayout {nsdecls("w")} w:type="fixed"/>')
    after = [qn(f"w:{t}") for t in ("tblCellMar", "tblLook", "tblCaption", "tblDescription")]
    nxt = next((el for el in tblPr if el.tag in after), None)
    if nxt is not None:
        nxt.addprevious(lay)
    else:
        tblPr.append(lay)
    grid = tbl._tbl.tblGrid
    for gc, w in zip(grid.findall(qn("w:gridCol")), t["widths"]):
        gc.set(qn("w:w"), str(int(w * 1440)))
    for j, h in enumerate(t["header"]):
        c = tbl.rows[0].cells[j]
        set_cell(c, h, t["widths"][j], bold=True, align="left" if j < 2 else "center", size=t.get("size", 8))
        border(c, "top", 8)
        border(c, "bottom", 4)
    for i, row in enumerate(t["rows"], start=1):
        for j, v in enumerate(row):
            c = tbl.rows[i].cells[j]
            set_cell(c, resolve(v), t["widths"][j], align="left" if j < 2 else "center",
                     size=t.get("size", 8))
            if i == len(t["rows"]):
                border(c, "bottom", 8)
    for r in tbl.rows:
        trPr = r._tr.get_or_add_trPr()
        trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        for c in r.cells:                  # keep the table and its footnote on one page
            for q in c.paragraphs:
                q.paragraph_format.keep_with_next = True
    note = DOC.add_paragraph(style="table copy")
    note.paragraph_format.space_before = Pt(2)
    note.paragraph_format.space_after = Pt(8)
    note.alignment = WD_ALIGN_PARAGRAPH.LEFT
    add_runs(note, resolve(t["note"]), size=7)


def add_box(key):
    """Shaded single-cell table spanning the column: bold title + numbered steps."""
    bx = BOXES[key]
    tbl = DOC.add_table(rows=1, cols=1)
    tbl.alignment = 1
    tbl.autofit = False
    tbl._tbl.tblGrid.findall(qn("w:gridCol"))[0].set(qn("w:w"), str(int(3.45 * 1440)))
    c = tbl.rows[0].cells[0]
    c.width = Inches(3.45)
    tcPr = c._tc.get_or_add_tcPr()
    b = parse_xml(f'<w:tcBorders {nsdecls("w")}>' + "".join(
        f'<w:{sd} w:val="single" w:sz="6" w:space="0" w:color="333333"/>' for sd in ("top", "left", "bottom", "right"))
        + "</w:tcBorders>")
    tcPr.append(b)
    tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="F2F6FA"/>'))
    tcPr.append(parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="60" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
                          f'<w:bottom w:w="60" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tcMar>'))
    p = c.paragraphs[0]
    p.style = DOC.styles["table copy"]
    p.paragraph_format.space_after = Pt(2)
    add_runs(p, bx["title"], size=8.5, base_bold=True)
    for k, item in enumerate(bx["items"], start=1):
        q = c.add_paragraph(style="table copy")
        q.paragraph_format.left_indent = Inches(0.14)
        q.paragraph_format.first_line_indent = Inches(-0.14)
        q.paragraph_format.space_after = Pt(1)
        q.alignment = WD_ALIGN_PARAGRAPH.LEFT
        add_runs(q, f"{k}. " + resolve(item), size=8.5)
    tr = tbl.rows[0]._tr.get_or_add_trPr()
    tr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
    gap = DOC.add_paragraph(style="Normal")
    gap.paragraph_format.space_after = Pt(4)
    gap.paragraph_format.space_before = Pt(0)


def add_figure(fname, caption):
    p = DOC.add_paragraph(style="Normal")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(FIG / fname), width=Inches(3.42))
    c = DOC.add_paragraph(style="figure caption")
    add_runs(c, resolve(caption))


# ───────────────────────────────────────────── build
DOC = docx.Document(str(TEMPLATE))
body = DOC.element.body
final_sect = body.sectPr
for child in list(body):
    if child is not final_sect:
        body.remove(child)
# final (last) section: 1 column, continuous -> Word balances the two body columns on the last page
for el in list(final_sect):
    final_sect.remove(el)
for el in sectpr(1, continuous=True):
    final_sect.append(copy.deepcopy(el))
# remove the template's copyright placeholder footer from the submission
for rel_id, rel in list(DOC.part.rels.items()):
    if rel.reltype.endswith("/footer"):
        pass  # footer part stays in the package but is no longer referenced

# title (section 1: one column)
tp = DOC.add_paragraph(style="paper title")
tp.add_run(TITLE)

# authors: two rows of three in a borderless full-width table (keeps the blocks aligned)
tp.paragraph_format.space_after = Pt(6)
atbl = DOC.add_table(rows=2, cols=3)
atbl.alignment = 1
atbl.autofit = False
for gc in atbl._tbl.tblGrid.findall(qn("w:gridCol")):
    gc.set(qn("w:w"), str(int(2.40 * 1440)))
for i, row in enumerate((AUTHORS[:3], AUTHORS[3:])):
    for j, (name, dept, org, place, email) in enumerate(row):
        cell = atbl.rows[i].cells[j]
        cell.width = Inches(2.40)
        p = cell.paragraphs[0]
        p.style = DOC.styles["Author"]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4 if i == 0 else 10)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(name)
        r.font.size = Pt(10)
        for txt, ital in [(dept, True), (org, True), (place, False), (email, False)]:
            if not txt:
                continue
            p.add_run().add_break()
            rr = p.add_run(txt)
            rr.italic = ital
            rr.font.size = Pt(9)
spacer = DOC.add_paragraph(style="Normal")
spacer.paragraph_format.space_after = Pt(4)
end_section(spacer, 1, continuous=False)

# abstract + keywords start the two-column body
ab = DOC.add_paragraph(style="Abstract")
ra = ab.add_run("Abstract")
ra.italic = True
ab.add_run("—" + resolve(ABSTRACT))
kw = DOC.add_paragraph(style="Keywords")
rk = kw.add_run("Keywords—")
rk.italic = True
rk.bold = True
kw.add_run(KEYWORDS)

for kind, payload in BODY:
    if kind == "h1":
        DOC.add_paragraph(payload, style="Heading 1")
    elif kind == "h2":
        DOC.add_paragraph(payload, style="Heading 2")
    elif kind == "p":
        add_runs(DOC.add_paragraph(style="Body Text"), resolve(payload))
    elif kind == "bullets":
        for b in payload:
            add_runs(DOC.add_paragraph(style="bullet list"), resolve(b))
    elif kind == "fig":
        add_figure(*payload)
    elif kind == "table":
        add_table(payload)
    elif kind == "box":
        add_box(payload)
    elif kind == "ack":
        DOC.add_paragraph("Acknowledgment", style="Heading 5").paragraph_format.keep_with_next = True
        add_runs(DOC.add_paragraph(style="Body Text"), resolve(payload))
    elif kind == "refs":
        DOC.add_paragraph("References", style="Heading 5").paragraph_format.keep_with_next = True
        last = None
        for k in ORDER:
            last = add_runs(DOC.add_paragraph(style="references"), REFS[k])
        end_section(last, 2)  # two-column body ends after the references

DOC.core_properties.title = TITLE.replace("\u2011", "-")
DOC.core_properties.author = "Ayush Arya; Neha Kriti; Harsha Kulkarni; Sarthak Srivastava; Shruti Kaushik; Varun Dutt"
DOC.save(str(OUT))

words = sum(len(re.findall(r"\w+", resolve(p))) for k, p in BODY if k == "p")
print(f"wrote {OUT}  body paragraphs ~{words} words; references {len(ORDER)}")
print("citation order:", ", ".join(f"[{i + 1}] {k}" for i, k in enumerate(ORDER)))
