"""
splitmatch/schema.py — the two typed interfaces of SPLIT-Match.

1. FactSheet  — what the EDGE tier extracts from a private patient note.
2. TrialProgram (of Atoms) — what the CLOUD tier compiles from public criteria.

Numbers are stored as closed intervals [lo, hi] (a point value is lo == hi).
Coarse statements ("1-3 months ago", "KPS 70" seen through an ECOG criterion)
therefore stay exact: three-valued evaluation returns U only when the interval
genuinely straddles a threshold.
"""
from __future__ import annotations

import math
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel as _PydBase, ConfigDict, Field, model_validator


class BaseModel(_PydBase):
    """Serialise +/-inf as Infinity (open-ended intervals must round-trip)."""
    model_config = ConfigDict(ser_json_inf_nan="constants")

INF = math.inf


# ════════════════════════════════════════════════════════════════════════
# Fact sheet (edge, private)
# ════════════════════════════════════════════════════════════════════════
class Status(str, Enum):
    VALUE = "value"                  # stated in the note
    NEGATED = "negated"              # explicitly absent ("no brain metastases")
    NOT_MENTIONED = "not_mentioned"  # the note is silent


class Kind(str, Enum):
    NUM = "num"        # interval-valued number
    BOOL = "bool"
    ENUM = "enum"
    TEXT = "text"


class FieldSpec(BaseModel):
    kind: Kind
    values: list[str] = []           # allowed enum values
    unit: str = ""
    cwa_default: Any = None          # pertinent negative: presumed value if unmentioned
    answerable_by: Literal["patient", "record", "clinician"] = "record"
    question: str = ""
    category: str = ""               # redaction category this field belongs to


BIOMARKER_VALUES = ["positive", "negative", "not_tested"]

# Field registry. `category` links fields to redaction categories (variants.py).
FIELDS: dict[str, FieldSpec] = {
    "age": FieldSpec(kind=Kind.NUM, unit="years", question="What is the patient's age?"),
    "sex": FieldSpec(kind=Kind.ENUM, values=["male", "female"], question="What is the patient's sex?"),
    "cancer_type": FieldSpec(kind=Kind.ENUM,
                             values=["nsclc", "sclc", "melanoma", "renal_cell", "mesothelioma", "other"],
                             question="What is the primary cancer type?"),
    "histology": FieldSpec(kind=Kind.ENUM,
                           values=["adenocarcinoma", "squamous", "large_cell", "nos", "other"],
                           question="What is the tumour histology (adenocarcinoma, squamous, ...)?"),
    "stage_group": FieldSpec(kind=Kind.ENUM, question="What is the current overall stage (e.g. IIIB, IV)?"),
    "tnm_t": FieldSpec(kind=Kind.TEXT), "tnm_n": FieldSpec(kind=Kind.TEXT),
    "tnm_m": FieldSpec(kind=Kind.TEXT),
    "measurable_disease": FieldSpec(kind=Kind.BOOL,
                                    question="Is there measurable disease on imaging (RECIST)?"),
    "disease_status": FieldSpec(kind=Kind.ENUM,
                                values=["newly_diagnosed", "progressed_after_prior", "recurrent",
                                        "stable_on_therapy"],
                                question="Is the disease newly diagnosed, progressing after prior "
                                         "therapy, recurrent, or stable on treatment?"),
    "ecog": FieldSpec(kind=Kind.NUM, category="PS", answerable_by="clinician",
                      question="What is the patient's ECOG performance status (0-4)?"),
    "kps": FieldSpec(kind=Kind.NUM, category="PS", answerable_by="clinician",
                     question="What is the patient's Karnofsky performance status?"),
    "fev1_pct": FieldSpec(kind=Kind.NUM, unit="% predicted", category="FEV1",
                          question="What is the FEV1 (% predicted) on pulmonary function testing?"),
    "fev1_l": FieldSpec(kind=Kind.NUM, unit="L", category="FEV1",
                        question="What is the FEV1 in litres?"),
    **{g: FieldSpec(kind=Kind.ENUM, values=BIOMARKER_VALUES, category="BIOMARKER",
                    question=f"What is the tumour's {g.upper()} status?")
       for g in ("egfr", "alk", "ros1", "kras", "ret", "braf", "met")},
    "egfr_detail": FieldSpec(kind=Kind.TEXT, category="BIOMARKER"),
    "pdl1_tps": FieldSpec(kind=Kind.NUM, unit="%", category="BIOMARKER",
                          question="What is the PD-L1 tumour proportion score?"),
    "brain_mets": FieldSpec(kind=Kind.ENUM, values=["none", "treated_stable", "untreated_or_symptomatic"],
                            cwa_default="none", category="BRAIN_METS",
                            question="Are there brain metastases, and if so are they treated and stable?"),
    "malignant_effusion": FieldSpec(kind=Kind.BOOL, category="EFFUSION",
                                    question="Is there a malignant pleural or pericardial effusion?"),
    "mi_months_ago": FieldSpec(kind=Kind.NUM, unit="months", category="CARDIAC",
                               question="Has the patient had a myocardial infarction, and when?"),
    "mi_history": FieldSpec(kind=Kind.BOOL, cwa_default=False, category="CARDIAC",
                            question="Has the patient ever had a myocardial infarction?"),
    "unstable_angina": FieldSpec(kind=Kind.BOOL, cwa_default=False, category="CARDIAC",
                                 question="Does the patient have recent or unstable angina?"),
    "chf": FieldSpec(kind=Kind.BOOL, cwa_default=False, category="CARDIAC",
                     question="Does the patient have congestive heart failure?"),
    "arrhythmia": FieldSpec(kind=Kind.ENUM, values=["none", "controlled", "uncontrolled"],
                            cwa_default="none", category="CARDIAC",
                            question="Does the patient have a cardiac arrhythmia, and is it controlled?"),
    "qtc_ms": FieldSpec(kind=Kind.NUM, unit="ms", category="CARDIAC", question="What is the QTc interval?"),
    "neuropathy_grade": FieldSpec(kind=Kind.NUM, cwa_default=0, question="Is there peripheral neuropathy, and what grade?"),
    "active_infection": FieldSpec(kind=Kind.BOOL, cwa_default=False, answerable_by="patient",
                                  question="Does the patient currently have an active infection needing treatment?"),
    "autoimmune_active": FieldSpec(kind=Kind.BOOL, cwa_default=False, answerable_by="patient",
                                   question="Does the patient have an active autoimmune disease?"),
    "steroids_systemic": FieldSpec(kind=Kind.BOOL, cwa_default=False, answerable_by="patient",
                                   question="Is the patient taking systemic corticosteroids?"),
    "pregnant": FieldSpec(kind=Kind.BOOL, cwa_default=False, answerable_by="patient",
                          question="Is the patient pregnant or breastfeeding?"),
    "life_expectancy_months": FieldSpec(kind=Kind.NUM, unit="months", answerable_by="clinician",
                                        question="What is the estimated life expectancy?"),
    # labs (canonical units)
    "creatinine_mg_dl": FieldSpec(kind=Kind.NUM, unit="mg/dL", category="LABS", question="What is the serum creatinine?"),
    "crcl_ml_min": FieldSpec(kind=Kind.NUM, unit="mL/min", category="LABS", question="What is the creatinine clearance?"),
    "bilirubin_mg_dl": FieldSpec(kind=Kind.NUM, unit="mg/dL", category="LABS", question="What is the total bilirubin?"),
    "ast_xuln": FieldSpec(kind=Kind.NUM, unit="xULN", category="LABS", question="What are the AST/ALT levels?"),
    "alt_xuln": FieldSpec(kind=Kind.NUM, unit="xULN", category="LABS", question="What are the AST/ALT levels?"),
    "anc_k_ul": FieldSpec(kind=Kind.NUM, unit="10^3/uL", category="LABS", question="What is the absolute neutrophil count?"),
    "wbc_k_ul": FieldSpec(kind=Kind.NUM, unit="10^3/uL", category="LABS", question="What is the white cell count?"),
    "platelets_k_ul": FieldSpec(kind=Kind.NUM, unit="10^3/uL", category="LABS", question="What is the platelet count?"),
    "hemoglobin_g_dl": FieldSpec(kind=Kind.NUM, unit="g/dL", category="LABS", question="What is the haemoglobin?"),
    "albumin_g_dl": FieldSpec(kind=Kind.NUM, unit="g/dL", category="LABS", question="What is the serum albumin?"),
}

# Reference upper limits of normal used ONLY for ×ULN conversions (approximate ⇒ never
# verified near a threshold; see evaluator).
ULN = {"bilirubin_mg_dl": 1.2, "creatinine_mg_dl": 1.2}
XULN_ALIASES = {"bilirubin_xuln": "bilirubin_mg_dl", "creatinine_xuln": "creatinine_mg_dl"}


class Fact(BaseModel):
    status: Status = Status.NOT_MENTIONED
    value: Any = None                      # NUM: [lo, hi]; BOOL: bool; ENUM/TEXT: str
    evidence: Optional[str] = None         # verbatim quote from the note
    readers: list[str] = []                # which readers produced this value
    verified: bool = False                 # two-reader agreement AND evidence grounds value

    @model_validator(mode="after")
    def _norm(self):
        if self.status is Status.VALUE and isinstance(self.value, (int, float)) \
                and not isinstance(self.value, bool):
            self.value = [float(self.value), float(self.value)]
        if isinstance(self.value, (list, tuple)) and len(self.value) == 2 \
                and all(isinstance(v, (int, float)) or v is None for v in self.value):
            lo, hi = self.value
            self.value = [float(lo) if lo is not None else -INF, float(hi) if hi is not None else INF]
        return self


THERAPY_CLASSES = ["chemo", "radio", "tki", "io", "antiangiogenic", "targeted_other", "systemic", "surgery", "other"]
SYSTEMIC_CLASSES = {"chemo", "tki", "io", "antiangiogenic", "targeted_other"}  # what "systemic (unspecified)" may be


class TherapyEvent(BaseModel):
    cls: Literal["chemo", "radio", "tki", "io", "antiangiogenic", "targeted_other", "systemic", "surgery", "other"]
    agents: list[str] = []
    line: Optional[int] = None                 # line of therapy in the advanced setting
    setting: Optional[str] = None              # adjuvant | neoadjuvant | advanced | definitive | palliative
    thoracic: Optional[bool] = None            # radiotherapy to the chest
    months_ago: Optional[list[Optional[float]]] = None   # interval since the LAST dose, [lo, hi]
    ongoing: Optional[bool] = None
    evidence: Optional[str] = None
    verified: bool = False

    @model_validator(mode="after")
    def _norm(self):
        if self.months_ago is not None:
            lo, hi = self.months_ago
            self.months_ago = [float(lo) if lo is not None else 0.0,
                               float(hi) if hi is not None else INF]
        return self


class FactSheet(BaseModel):
    patient_id: str
    fields: dict[str, Fact] = Field(default_factory=dict)
    therapy_status: Status = Status.NOT_MENTIONED   # NEGATED = "no prior therapy" stated
    events: list[TherapyEvent] = []
    lines_of_therapy: Optional[list[Optional[float]]] = None  # interval of #prior advanced-setting lines
    reader_meta: dict = {}

    def get(self, name: str) -> Fact:
        return self.fields.get(name, Fact())


# ════════════════════════════════════════════════════════════════════════
# Trial program (cloud, public)
# ════════════════════════════════════════════════════════════════════════
class AtomType(str, Enum):
    CMP = "CMP"          # numeric comparison on a field
    IN = "IN"            # field value in a set (stage uses subsumption)
    IS = "IS"            # boolean field equals true/false
    HAS = "HAS"          # some therapy event matches a filter
    COUNT = "COUNT"      # number of prior lines / matching events vs k
    WITHIN = "WITHIN"    # a matching event's last dose within the past X months
    SINCE = "SINCE"      # ALL matching events ended at least X months ago (washout satisfied)
    IF = "IF"            # children[0] -> children[1]  (Kleene implication)
    ANY = "ANY"          # OR over children
    ALL = "ALL"          # AND over children
    JUDGE = "JUDGE"      # irreducibly semantic; resolved by the ladder
    UNSCREENABLE = "UNSCREENABLE"  # not decidable at pre-screening (consent, contraception...)


CMP_OPS = ["<", "<=", ">", ">=", "==", "!="]


class EventFilter(BaseModel):
    cls: list[str] = []          # therapy classes (empty = any)
    agents: list[str] = []       # specific agents/drug classes (lower-case substrings)
    thoracic: Optional[bool] = None
    setting: list[str] = []


class Atom(BaseModel):
    id: str
    type: AtomType
    polarity: Literal["inclusion", "exclusion"] = "inclusion"
    source_line: str = ""                 # verbatim criterion text (audit)
    lines: list[int] = []                 # numbered criterion lines this atom encodes
    section: Optional[str] = None         # "inclusion" | "exclusion" section of its source line
    cwa: bool = False                     # JUDGE only: an adverse finding presumed absent if unmentioned
    field: Optional[str] = None
    op: Optional[str] = None
    value: Any = None
    values: list[Any] = []
    filter: Optional[EventFilter] = None
    k: Optional[float] = None
    months: Optional[float] = None
    text: Optional[str] = None            # JUDGE / UNSCREENABLE description
    children: list["Atom"] = []
    downgraded: bool = False              # compiler disagreement ⇒ no deterministic authority
    answerable_by: Literal["patient", "record", "clinician"] = "record"
    question: Optional[str] = None


class TrialProgram(BaseModel):
    trial_id: str
    atoms: list[Atom]
    compiler_meta: dict = {}


# ════════════════════════════════════════════════════════════════════════
# Type checker (deterministic; rejects malformed compiler output)
# ════════════════════════════════════════════════════════════════════════
def type_errors(atom: Atom, path: str = "") -> list[str]:
    p = f"{path}{atom.id}"
    errs: list[str] = []
    t = atom.type
    if t in (AtomType.CMP, AtomType.IN, AtomType.IS):
        if atom.field is None:
            return [f"{p}: {t.value} needs field"]
        fname = XULN_ALIASES.get(atom.field, atom.field)
        if fname not in FIELDS:
            return [f"{p}: unknown field {atom.field!r}"]
        spec = FIELDS[fname]
        if t is AtomType.CMP:
            if spec.kind is not Kind.NUM:
                errs.append(f"{p}: CMP on non-numeric field {atom.field}")
            if atom.op not in CMP_OPS:
                errs.append(f"{p}: bad op {atom.op!r}")
            if not isinstance(atom.value, (int, float)) or isinstance(atom.value, bool):
                errs.append(f"{p}: CMP value must be a number")
        elif t is AtomType.IN:
            if not atom.values:
                errs.append(f"{p}: IN needs values")
            if spec.kind is Kind.ENUM and spec.values and fname != "stage_group":
                bad = [v for v in atom.values if str(v) not in spec.values]
                if bad:
                    errs.append(f"{p}: values {bad} not in {spec.values}")
        elif t is AtomType.IS:
            if spec.kind is not Kind.BOOL or not isinstance(atom.value, bool):
                errs.append(f"{p}: IS needs a boolean field and a boolean value")
    elif t in (AtomType.HAS, AtomType.WITHIN, AtomType.SINCE, AtomType.COUNT):
        f = atom.filter or EventFilter()
        bad = [c for c in f.cls if c not in THERAPY_CLASSES]
        if bad:
            errs.append(f"{p}: unknown therapy classes {bad}")
        if t in (AtomType.WITHIN, AtomType.SINCE) and (atom.months is None or atom.months < 0):
            errs.append(f"{p}: {t.value} needs months >= 0")
        if t is AtomType.COUNT and (atom.k is None or atom.op not in CMP_OPS):
            errs.append(f"{p}: COUNT needs op and k")
    elif t is AtomType.IF:
        if len(atom.children) != 2:
            errs.append(f"{p}: IF needs exactly 2 children")
    elif t in (AtomType.ANY, AtomType.ALL):
        if len(atom.children) < 2:
            errs.append(f"{p}: {t.value} needs >= 2 children")
    elif t in (AtomType.JUDGE, AtomType.UNSCREENABLE):
        if not (atom.text or atom.source_line):
            errs.append(f"{p}: {t.value} needs text")
    for c in atom.children:
        errs += type_errors(c, path=p + ".")
    return errs


def program_errors(prog: TrialProgram) -> list[str]:
    errs = []
    ids = [a.id for a in prog.atoms]
    if len(ids) != len(set(ids)):
        errs.append("duplicate atom ids")
    for a in prog.atoms:
        errs += type_errors(a)
    return errs
