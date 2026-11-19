#!/usr/bin/env python3
"""
Oxford School & College Sundovi - Scholarship Test Result 2026
Excel -> public JSON + private office workbook converter.

The original workbook is NEVER modified. A separate office-only workbook
(Result_with_Pass_Fail.xlsx) is written next to this project and is excluded
from Git and Vercel. Only data/results.json is published.

Usage:
    python tools/convert.py [path/to/source.xlsx]
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ----------------------------------------------------------------------------
# CONFIGURATION - change these values only, not the processing logic below.
# ----------------------------------------------------------------------------
PASSING_MARKS = 29
DEFAULT_TOTAL_MARKS = 100
SHEET_ALL = "All Students Marks Sheet"
SHEET_TOP = "Top 3 Achievers"
PUBLIC_JSON_NAME = "results.json"
PRIVATE_WORKBOOK_NAME = "Result_with_Pass_Fail.xlsx"

# Public-authorisation switches. The school management must approve these.
# Contact numbers are NEVER written to the public JSON under any setting.
PUBLISH_FATHER_NAME = True
PUBLISH_SCHOOL_NAME = True

INSTITUTION = "Oxford School & College Sundovi"
EVENT = "Annual Scholarship Test 2026"
TEST_DATE = "15 November 2026"
ORDERED_CLASSES = ["3rd", "4th", "5th", "6th", "7th", "8th", "9th"]

SCHOLARSHIP_BY_POSITION = {1: "100%", 2: "60%", 3: "40%"}

# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------

log_lines: list[str] = []


def log(message: str = "") -> None:
    print(message)
    log_lines.append(message)


def clean_text(value) -> str:
    """Trim and collapse whitespace without changing spelling or case."""
    if value is None:
        return ""
    text = str(value).replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return "" if text.lower() in {"none", "nan", "null", "-", "--"} else text


def normalise_name(value) -> str:
    """Preserve identity: only fix whitespace and typography, never spelling/case."""
    name = clean_text(value)
    name = name.replace("`", "'").replace("\u2018", "'").replace("\u2019", "'")
    name = re.sub(r"\s+", " ", name).strip()
    return name


def normalise_class(value) -> str:
    raw = clean_text(value).lower()
    if not raw:
        return ""
    match = re.search(r"(\d{1,2})", raw)
    if not match:
        return clean_text(value)
    number = int(match.group(1))
    if 1 <= number <= 12:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
        if 10 <= number % 100 <= 20:
            suffix = "th"
        return f"{number}{suffix}"
    return clean_text(value)


def parse_number(value):
    """Return int/float or None. Blank cells mean absent."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if float(value).is_integer() else round(float(value), 2)
    text = clean_text(value).replace(",", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return int(number) if number.is_integer() else round(number, 2)


def parse_roll(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return clean_text(value).replace(" ", "")


def ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def competition_ranks(items: list[dict], key: str) -> None:
    """Competition (1224) ranking. Absent students are not passed in."""
    appeared = [item for item in items if item["obtained"] is not None]
    for item in appeared:
        item[key] = None
    sorted_items = sorted(appeared, key=lambda item: -item["obtained"])
    for item in sorted_items:
        higher = sum(1 for other in sorted_items if other["obtained"] > item["obtained"])
        item[key] = higher + 1


# ----------------------------------------------------------------------------
# Excel reading
# ----------------------------------------------------------------------------


def find_source_workbook(root: Path, explicit: str | None) -> Path:
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if not candidate.is_file():
            raise SystemExit(f"Source workbook not found: {candidate}")
        return candidate
    candidates: list[Path] = []
    for directory in (root, root / "private", root / "_source"):
        if not directory.is_dir():
            continue
        candidates.extend(sorted(directory.glob("*.xlsx")))
    if not candidates:
        raise SystemExit(
            "No .xlsx workbook found. Place the original Excel file in the project "
            "folder or pass its path: python tools/convert.py path/to/file.xlsx"
        )
    preferred = [p for p in candidates if "Marks_Entry" in p.name or "Marks Sheet" in p.name]
    return (preferred or candidates)[0]


def column_map(header_row: tuple) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, cell in enumerate(header_row):
        label = clean_text(cell).lower()
        if not label:
            continue
        label = label.replace("'", "").replace("/", " ").replace("(", "").replace(")", "")
        label = label.replace(".", " ").replace(",", " ")
        label = re.sub(r"\s+", " ", label).strip()
        mapping[label] = index
    return mapping


def pick(mapping: dict[str, int], row: tuple, *labels: str):
    for label in labels:
        if label in mapping and mapping[label] < len(row):
            return row[mapping[label]]
    return None


def read_max_marks(ws, header_index: int, mapping: dict[str, int]) -> int:
    """The workbook stores maximum marks in a highlighted cell near the top."""
    for row in ws.iter_rows(min_row=1, max_row=header_index, values_only=True):
        for value in row:
            text = clean_text(value).lower()
            if "maximum" in text and "mark" in text:
                for candidate in row:
                    number = parse_number(candidate)
                    if number and 0 < number <= 1000:
                        return int(number)
    for row in ws.iter_rows(min_row=1, max_row=header_index, values_only=True):
        for value in row:
            number = parse_number(value)
            if number and 0 < number <= 1000:
                return int(number)
    return DEFAULT_TOTAL_MARKS


def read_students(workbook, stats: dict) -> list[dict]:
    ws = workbook[SHEET_ALL]
    rows = list(ws.iter_rows(values_only=True))

    header_index = None
    mapping: dict[str, int] = {}
    for index, row in enumerate(rows):
        if any("s.no" in clean_text(cell).lower() for cell in row):
            header_index = index
            mapping = column_map(row)
            break
    if header_index is None:
        raise SystemExit(f"Could not find the header row in sheet '{SHEET_ALL}'.")

    total_marks = read_max_marks(ws, header_index + 1, mapping)
    stats["total_marks"] = total_marks
    log(f"Maximum marks read from workbook: {total_marks}")

    students: list[dict] = []
    skipped_footer = 0
    skipped_empty = 0
    seen_rolls: dict[str, int] = {}
    cleaning: list[str] = []

    for row in rows[header_index + 1:]:
        first = clean_text(row[0] if row else None)
        if first.lower().startswith(("overall", "summary", "grand total")):
            skipped_footer += 1
            continue

        raw = {
            "sno": pick(mapping, row, "sno", "s no"),
            "roll": pick(mapping, row, "roll no", "rollnumber"),
            "name": pick(mapping, row, "student s full name", "students full name", "student full name", "name"),
            "father": pick(mapping, row, "fathers guardians name", "father guardian name", "fathers name", "guardian name", "father name"),
            "class": pick(mapping, row, "class"),
            "school": pick(mapping, row, "current school name", "school name", "school"),
            "contact": pick(mapping, row, "contact number", "contact"),
            "total": pick(mapping, row, "total marks", "total"),
            "obtained": pick(mapping, row, "obtained marks", "obtained", "marks obtained"),
            "pct": pick(mapping, row, "percentage", "percentage %"),
        }

        if not any(clean_text(raw[key]) for key in ("roll", "name", "class", "obtained")):
            skipped_empty += 1
            continue

        original_name = str(raw["name"] or "")
        name = normalise_name(raw["name"])
        if original_name != name:
            cleaning.append(f"Whitespace normalised in name: '{original_name}' -> '{name}'")

        original_class = clean_text(raw["class"])
        cls = normalise_class(original_class)
        if original_class != cls:
            cleaning.append(f"Class normalised: '{original_class}' -> '{cls}'")

        roll = parse_roll(raw["roll"])
        if not roll:
            cleaning.append(f"Missing roll number for student '{name}' ({cls})")
        if roll and not roll.isdigit():
            cleaning.append(f"Roll number contains non-digit characters: '{roll}' ({name})")
        if roll in seen_rolls:
            cleaning.append(
                f"DUPLICATE ROLL NUMBER '{roll}': '{name}' ({cls}) and "
                f"'{students[seen_rolls[roll]]['name']}' ({students[seen_rolls[roll]]['class']})"
            )
        else:
            seen_rolls[roll] = len(students)

        raw_obtained = raw["obtained"]
        obtained = parse_number(raw_obtained)
        if obtained is not None and not isinstance(raw_obtained, (int, float)) and clean_text(raw_obtained):
            cleaning.append(f"Marks converted from text: '{clean_text(raw_obtained)}' -> {obtained} ({name})")
        if obtained is None and clean_text(raw_obtained):
            cleaning.append(f"Invalid marks '{clean_text(raw_obtained)}' treated as absent ({name})")
        if obtained is not None and (obtained < 0 or obtained > total_marks):
            cleaning.append(f"Out-of-range marks {obtained} for {name} ({cls})")
        if obtained == 0:
            cleaning.append(f"Zero marks kept as appeared (not absent): {name} ({roll})")

        record_total = parse_number(raw["total"])
        if record_total is None:
            record_total = total_marks
        else:
            record_total = int(record_total)

        percentage = round((obtained / record_total) * 100, 2) if obtained is not None else None
        source_pct = parse_number(raw["pct"])
        if percentage is not None and source_pct is not None and abs(source_pct - percentage) > 0.01:
            cleaning.append(f"Percentage recalculated for {name}: {source_pct} -> {percentage}")

        if obtained is None:
            status = "Absent"
        elif obtained >= PASSING_MARKS:
            status = "Pass"
        else:
            status = "Appeared"

        students.append(
            {
                "rollNo": roll,
                "name": name,
                "fatherName": normalise_name(raw["father"]) if PUBLISH_FATHER_NAME else None,
                "class": cls,
                "school": normalise_name(raw["school"]) if PUBLISH_SCHOOL_NAME else None,
                "total": record_total,
                "obtained": obtained,
                "percentage": percentage,
                "classPosition": None,
                "overallPosition": None,
                "status": status,
                "scholarship": None,
                # private working fields (never written to public JSON)
                "_row": len(students) + header_index + 2,
                "_review": [],
            }
        )

    stats["skipped_footer_rows"] = skipped_footer
    stats["skipped_empty_rows"] = skipped_empty
    stats["cleaning"] = cleaning
    return students


def cross_check_toppers(workbook, students: list[dict]) -> None:
    """Read the school's own Top 3 Achievers sheet and report differences."""
    if SHEET_TOP not in workbook.sheetnames:
        log(f"NOTE: Worksheet '{SHEET_TOP}' is missing from the source workbook.")
        return
    ws = workbook[SHEET_TOP]
    issues = 0
    for row in ws.iter_rows(min_row=1, values_only=True):
        cells = [clean_text(cell) for cell in row]
        if not cells or cells[0].lower() not in [c.lower() for c in ORDERED_CLASSES]:
            continue
        cls = normalise_class(cells[0])
        roll = cells[2].replace(" ", "")
        expected_pos = 1 if "1" in cells[1] else 2 if "2" in cells[1] else 3 if "3" in cells[1] else None
        match = next((s for s in students if s["rollNo"] == roll and s["class"] == cls), None)
        if not match:
            log(f"TOP-3 CHECK: roll {roll} ({cls}) from achievers sheet not found in main sheet.")
            issues += 1
        elif expected_pos and match["classPosition"] != expected_pos:
            log(
                f"TOP-3 CHECK DIFFERENCE: roll {roll} ({cls}) school sheet says position "
                f"{expected_pos}, calculated position {match['classPosition']}."
            )
            issues += 1
    log(f"Top 3 Achievers cross-check: {issues} difference(s) found.")


# ----------------------------------------------------------------------------
# Ranking, scholarships, statistics
# ----------------------------------------------------------------------------


def calculate_rankings(students: list[dict]) -> dict:
    by_class: dict[str, list[dict]] = defaultdict(list)
    for student in students:
        if student["class"]:
            by_class[student["class"]].append(student)
        else:
            log(f"WARNING: Missing class for roll {student['rollNo']} ({student['name']})")

    for cls, group in by_class.items():
        competition_ranks(group, "classPosition")
    competition_ranks(students, "overallPosition")

    ties: dict[str, list[str]] = {"class": [], "overall": []}

    for cls in ORDERED_CLASSES:
        group = [s for s in by_class.get(cls, []) if s["obtained"] is not None]
        by_marks = defaultdict(list)
        for student in group:
            by_marks[student["obtained"]].append(student)
        for marks, members in sorted(by_marks.items(), reverse=True):
            if len(members) > 1:
                names = ", ".join(f"{s['name']} (roll {s['rollNo']})" for s in members)
                line = (
                    f"CLASS TIE - {cls}, {marks} marks, shared position "
                    f"{ordinal(members[0]['classPosition'])}: {names}"
                )
                ties["class"].append(line)

    by_marks_all = defaultdict(list)
    for student in students:
        if student["obtained"] is not None:
            by_marks_all[student["obtained"]].append(student)
    for marks, members in sorted(by_marks_all.items(), reverse=True):
        if len(members) > 1:
            names = ", ".join(
                f"{s['name']} (roll {s['rollNo']}, class {s['class']})" for s in members
            )
            ties["overall"].append(
                f"OVERALL TIE - {marks} marks, shared position "
                f"{ordinal(members[0]['overallPosition'])}: {names}"
            )

    log("")
    log("ALL CLASS-WISE RANKING TIES:")
    log("\n".join(ties["class"]) if ties["class"] else "  None")
    log("")
    log("ALL OVERALL RANKING TIES:")
    log("\n".join(ties["overall"]) if ties["overall"] else "  None")
    log("")

    # Scholarships are based on CLASS position only. Ties are never silently
    # resolved and no tie-breaking rule is invented.
    review_cases: list[str] = []
    for cls in ORDERED_CLASSES:
        by_position = defaultdict(list)
        for student in by_class.get(cls, []):
            if student["classPosition"] in SCHOLARSHIP_BY_POSITION:
                by_position[student["classPosition"]].append(student)
        for position in (1, 2, 3):
            members = by_position.get(position, [])
            if len(members) > 1:
                names = ", ".join(f"{s['name']} (roll {s['rollNo']})" for s in members)
                message = (
                    f"MANAGEMENT REVIEW - {cls}: {len(members)} students share "
                    f"{ordinal(position)} position ({names}). Scholarship withheld pending "
                    f"school management decision."
                )
                review_cases.append(message)
                for student in members:
                    student["_review"].append(f"Tied {ordinal(position)} position")
                    student["scholarship"] = None
            else:
                for student in members:
                    if student["obtained"] is not None and student["obtained"] < PASSING_MARKS:
                        message = (
                            f"MANAGEMENT REVIEW - {cls}: {student['name']} (roll "
                            f"{student['rollNo']}) is {ordinal(position)} with "
                            f"{student['obtained']} marks (< {PASSING_MARKS}). Scholarship "
                            f"withheld pending management decision."
                        )
                        review_cases.append(message)
                        student["_review"].append("Top-three position below passing marks")
                        student["scholarship"] = None
                    else:
                        student["scholarship"] = SCHOLARSHIP_BY_POSITION[position]

    log("SCHOLARSHIP REVIEW CASES:")
    log("\n".join(review_cases) if review_cases else "  None")
    log("")
    return {"ties": ties, "review_cases": review_cases, "by_class": by_class}


def build_statistics(students: list[dict], by_class: dict[str, list[dict]], total_marks: int) -> dict:
    appeared = [s for s in students if s["obtained"] is not None]
    passed = [s for s in students if s["status"] == "Pass"]
    below = [s for s in students if s["status"] == "Appeared"]
    absent = [s for s in students if s["status"] == "Absent"]

    class_stats = []
    for cls in ORDERED_CLASSES:
        group = by_class.get(cls, [])
        class_stats.append(
            {
                "class": cls,
                "registered": len(group),
                "appeared": sum(1 for s in group if s["obtained"] is not None),
                "absent": sum(1 for s in group if s["obtained"] is None),
                "passed": sum(1 for s in group if s["status"] == "Pass"),
                "belowPassing": sum(1 for s in group if s["status"] == "Appeared"),
                "toppers": [
                    {
                        "rollNo": s["rollNo"],
                        "name": s["name"],
                        "marks": s["obtained"],
                        "classPosition": s["classPosition"],
                        "overallPosition": s["overallPosition"],
                        "scholarship": s["scholarship"],
                    }
                    for s in sorted(
                        [x for x in group if x["classPosition"] in (1, 2, 3)],
                        key=lambda x: (x["classPosition"], x["rollNo"]),
                    )
                ],
            }
        )

    overall_top = [
        {
            "rollNo": s["rollNo"],
            "name": s["name"],
            "class": s["class"],
            "marks": s["obtained"],
            "overallPosition": s["overallPosition"],
        }
        for s in sorted(
            [x for x in students if x["overallPosition"] is not None],
            key=lambda x: (x["overallPosition"], x["rollNo"]),
        )[:10]
    ]

    return {
        "totalRegistered": len(students),
        "appeared": len(appeared),
        "absent": len(absent),
        "passed": len(passed),
        "belowPassing": len(below),
        "numberOfClasses": len([c for c in ORDERED_CLASSES if by_class.get(c)]),
        "totalMarks": total_marks,
        "passingMarks": PASSING_MARKS,
        "classes": class_stats,
        "overallTop": overall_top,
    }


# ----------------------------------------------------------------------------
# Output writers
# ----------------------------------------------------------------------------


def write_public_json(root: Path, students: list[dict], statistics: dict) -> Path:
    public = []
    for student in students:
        public.append(
            {
                "rollNo": student["rollNo"],
                "name": student["name"],
                "fatherName": student["fatherName"] or None,
                "class": student["class"],
                "school": student["school"] or None,
                "total": student["total"],
                "obtained": student["obtained"],
                "percentage": student["percentage"],
                "classPosition": student["classPosition"],
                "overallPosition": student["overallPosition"],
                "status": student["status"],
                "scholarship": student["scholarship"],
            }
        )
    payload = {
        "meta": {
            "institution": INSTITUTION,
            "event": EVENT,
            "testDate": TEST_DATE,
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "classes": ORDERED_CLASSES,
            "statistics": statistics,
        },
        "students": public,
    }
    path = root / "data" / PUBLIC_JSON_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Written public data: {path}")
    return path


FILLS = {
    "Pass": PatternFill("solid", fgColor="C6EFCE"),
    "Fail": PatternFill("solid", fgColor="FFC7CE"),
    "Absent": PatternFill("solid", fgColor="E7E6E6"),
    1: PatternFill("solid", fgColor="FFD700"),
    2: PatternFill("solid", fgColor="D9D9D9"),
    3: PatternFill("solid", fgColor="CD7F32"),
}
HEADER_FILL = PatternFill("solid", fgColor="102A43")
HEADER_FONT = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
THIN = Side(style="thin", color="B7C3D0")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def style_header(ws, row: int, columns: int) -> None:
    for column in range(1, columns + 1):
        cell = ws.cell(row=row, column=column)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER


def write_private_workbook(
    root: Path, source: Path, students: list[dict], statistics: dict, review_cases: list[str]
) -> Path:
    workbook = openpyxl.load_workbook(source)
    ws = workbook[SHEET_ALL]

    header_row = None
    mapping: dict[str, int] = {}
    for index, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if any("s.no" in clean_text(cell).lower() for cell in row):
            header_row = index
            mapping = column_map(row)
            break
    if header_row is None:
        raise SystemExit("Could not locate the header row for office workbook output.")

    def col(label: str, *alternatives: str) -> int:
        for name in (label, *alternatives):
            if name in mapping:
                return mapping[name] + 1
        return 0

    columns = {
        "total": col("total marks", "total"),
        "obtained": col("obtained marks", "obtained"),
        "pct": col("percentage", "percentage %"),
        "cp": col("class position"),
        "op": col("overall position"),
        "status": col("remarks status", "remarks"),
    }
    for student in students:
        row_number = student["_row"]
        values = {
            "total": student["total"],
            "obtained": student["obtained"] if student["obtained"] is not None else None,
            "pct": student["percentage"],
            "cp": student["classPosition"],
            "op": student["overallPosition"],
            "status": {"Pass": "Pass", "Appeared": "Fail", "Absent": "Absent"}[student["status"]],
        }
        for key, column in columns.items():
            if column:
                ws.cell(row=row_number, column=column, value=values[key])

        if columns["status"]:
            ws.cell(row=row_number, column=columns["status"]).fill = FILLS[values["status"]]
        if columns["cp"] and student["classPosition"] in FILLS:
            ws.cell(row=row_number, column=columns["cp"]).fill = FILLS[student["classPosition"]]
        if columns["op"] and student["overallPosition"] in FILLS:
            ws.cell(row=row_number, column=columns["op"]).fill = FILLS[student["overallPosition"]]

    if "Summary" in workbook.sheetnames:
        del workbook["Summary"]
    summary = workbook.create_sheet("Summary")
    row = 1

    def section(title: str) -> None:
        nonlocal row
        cell = summary.cell(row=row, column=1, value=title)
        cell.font = Font(bold=True, size=13, color="102A43")
        row += 1

    def table(headers: list[str], data: list[list]) -> None:
        nonlocal row
        for index, header in enumerate(headers, start=1):
            summary.cell(row=row, column=index, value=header)
        style_header(summary, row, len(headers))
        row += 1
        for record in data:
            for index, value in enumerate(record, start=1):
                cell = summary.cell(row=row, column=index, value=value)
                cell.border = BORDER
            row += 1
        row += 1

    section("Oxford School & College Sundovi - Scholarship Test 2026 - Summary")
    table(
        ["Metric", "Value"],
        [
            ["Total registered students", statistics["totalRegistered"]],
            ["Total appeared", statistics["appeared"]],
            ["Total absent", statistics["absent"]],
            ["Total passed", statistics["passed"]],
            ["Total below passing marks", statistics["belowPassing"]],
            ["Passing marks", PASSING_MARKS],
            ["Maximum marks", statistics["totalMarks"]],
            ["Generated at (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")],
        ],
    )
    section("Class-wise statistics")
    table(
        ["Class", "Registered", "Appeared", "Absent", "Passed", "Below passing"],
        [
            [
                item["class"], item["registered"], item["appeared"], item["absent"],
                item["passed"], item["belowPassing"],
            ]
            for item in statistics["classes"]
        ],
    )
    section("Class-wise top three")
    table(
        ["Class", "Position", "Roll No.", "Student", "Marks", "Overall", "Scholarship"],
        [
            [
                item["class"], ordinal(top["classPosition"]), top["rollNo"], top["name"],
                top["marks"], ordinal(top["overallPosition"]) if top["overallPosition"] else "-",
                top["scholarship"] or "UNDER REVIEW",
            ]
            for item in statistics["classes"]
            for top in item["toppers"]
        ],
    )
    section("Scholarship management review cases")
    table(["Case"], [[case] for case in review_cases] or [["None"]])

    summary.column_dimensions["A"].width = 30
    for letter in "BCDEFG":
        summary.column_dimensions[letter].width = 20
    summary.freeze_panes = "A2"

    path = root / PRIVATE_WORKBOOK_NAME
    workbook.save(path)
    log(f"Written PRIVATE office workbook (do not publish): {path}")
    return path


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    source = find_source_workbook(root, sys.argv[1] if len(sys.argv) > 1 else None)
    log(f"Source workbook: {source}")
    log("=" * 78)

    values_workbook = openpyxl.load_workbook(source, data_only=True)
    missing = [name for name in (SHEET_ALL, SHEET_TOP) if name not in values_workbook.sheetnames]
    if SHEET_ALL in missing:
        raise SystemExit(f"Required worksheet '{SHEET_ALL}' not found. Found: {values_workbook.sheetnames}")
    log(f"Worksheets found: {', '.join(values_workbook.sheetnames)}")

    stats: dict = {}
    students = read_students(values_workbook, stats)
    ranking = calculate_rankings(students)
    cross_check_toppers(values_workbook, students)
    statistics = build_statistics(students, ranking["by_class"], stats["total_marks"])

    log("")
    log("DATA CLEANING / VALIDATION LOG:")
    log("\n".join(f"  - {item}" for item in stats["cleaning"]) if stats["cleaning"] else "  - No changes required")
    log(f"  - Footer rows skipped: {stats['skipped_footer_rows']}")
    log(f"  - Empty rows skipped: {stats['skipped_empty_rows']}")

    log("")
    log("=" * 78)
    log("FINAL STATISTICS")
    log(f"  Total registered students : {statistics['totalRegistered']}")
    log(f"  Students appeared         : {statistics['appeared']}")
    log(f"  Students absent           : {statistics['absent']}")
    log(f"  Students passed           : {statistics['passed']}")
    log(f"  Students below passing    : {statistics['belowPassing']}")
    log(f"  Number of classes         : {statistics['numberOfClasses']}")
    for item in statistics["classes"]:
        log(
            f"  {item['class']:>4} : registered {item['registered']:>3}, appeared {item['appeared']:>3}, "
            f"absent {item['absent']:>3}, passed {item['passed']:>3}, below {item['belowPassing']:>3}"
        )
    log("")
    log("CLASS-WISE TOPPERS")
    for item in statistics["classes"]:
        tops = ", ".join(
            f"{ordinal(t['classPosition'])} {t['name']} ({t['marks']} marks, "
            f"overall {ordinal(t['overallPosition'])}, {t['scholarship'] or 'REVIEW'})"
            for t in item["toppers"]
        )
        log(f"  {item['class']}: {tops}")
    log("")
    log("OVERALL TOP 10")
    for top in statistics["overallTop"]:
        log(
            f"  {ordinal(top['overallPosition']):>5}: {top['name']} (class {top['class']}, "
            f"roll {top['rollNo']}, {top['marks']} marks)"
        )
    log("=" * 78)

    write_public_json(root, students, statistics)
    write_private_workbook(root, source, students, statistics, ranking["review_cases"])
    log("")
    log("Conversion complete. Only data/results.json is safe to publish.")


if __name__ == "__main__":
    main()
