import argparse
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
FONT_PATH = Path(r"C:\Windows\Fonts\simhei.ttf")


def register_fonts():
    pdfmetrics.registerFont(TTFont("NotoSC", str(FONT_PATH)))
    pdfmetrics.registerFont(TTFont("NotoSC-Bold", str(FONT_PATH)))


def make_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="NotoSC-Bold",
            fontSize=24,
            leading=32,
            textColor=colors.HexColor("#103f4a"),
            alignment=TA_LEFT,
            wordWrap="CJK",
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            fontName="NotoSC",
            fontSize=12,
            leading=19,
            textColor=colors.HexColor("#243f46"),
            wordWrap="CJK",
            spaceAfter=14,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="NotoSC-Bold",
            fontSize=16,
            leading=24,
            textColor=colors.HexColor("#103f4a"),
            wordWrap="CJK",
            spaceBefore=14,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName="NotoSC",
            fontSize=9.6,
            leading=16,
            textColor=colors.HexColor("#1f2d33"),
            wordWrap="CJK",
            spaceAfter=8,
        ),
        "quote": ParagraphStyle(
            "quote",
            parent=base["BodyText"],
            fontName="NotoSC-Bold",
            fontSize=10.5,
            leading=17,
            textColor=colors.HexColor("#103f4a"),
            backColor=colors.HexColor("#eaf4f3"),
            borderColor=colors.HexColor("#a7cccc"),
            borderWidth=0.6,
            borderPadding=8,
            wordWrap="CJK",
            spaceBefore=4,
            spaceAfter=12,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["BodyText"],
            fontName="NotoSC",
            fontSize=9.3,
            leading=15,
            leftIndent=13,
            firstLineIndent=-8,
            textColor=colors.HexColor("#1f2d33"),
            wordWrap="CJK",
            spaceAfter=4,
        ),
        "table": ParagraphStyle(
            "table",
            parent=base["BodyText"],
            fontName="NotoSC",
            fontSize=8.0,
            leading=12,
            textColor=colors.HexColor("#1f2d33"),
            wordWrap="CJK",
        ),
        "table_header": ParagraphStyle(
            "table_header",
            parent=base["BodyText"],
            fontName="NotoSC-Bold",
            fontSize=8.1,
            leading=12,
            textColor=colors.white,
            alignment=TA_CENTER,
            wordWrap="CJK",
        ),
    }


def esc(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("**", "")
        .replace("`", "")
    )


def parse_table(lines, start):
    rows = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        raw = lines[i].strip().strip("|")
        rows.append([cell.strip() for cell in raw.split("|")])
        i += 1
    if len(rows) >= 2 and all(set(cell.replace(":", "").strip()) <= {"-"} for cell in rows[1]):
        rows.pop(1)
    return rows, i


def table_widths(row_count, col_count):
    usable = 7.15 * inch
    if col_count == 2:
        return [usable * 0.32, usable * 0.68]
    if col_count == 3:
        return [usable * 0.24, usable * 0.51, usable * 0.25]
    if col_count == 4:
        return [usable * 0.17, usable * 0.29, usable * 0.34, usable * 0.20]
    return [usable / col_count] * col_count


def build_story(markdown, styles):
    lines = markdown.splitlines()
    story = []
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        if stripped.startswith("|"):
            rows, i = parse_table(lines, i)
            if not rows:
                continue
            col_count = max(len(row) for row in rows)
            data = []
            for r, row in enumerate(rows):
                padded = row + [""] * (col_count - len(row))
                style = styles["table_header"] if r == 0 else styles["table"]
                data.append([Paragraph(esc(cell), style) for cell in padded])
            table = Table(data, colWidths=table_widths(len(rows), col_count), repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#103f4a")),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#bdccd0")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7f7")]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 8))
            continue

        if stripped.startswith("# "):
            text = stripped[2:].strip()
            style_name = "title" if not story else "h2"
            story.append(Paragraph(esc(text), styles[style_name]))
            i += 1
            continue

        if stripped.startswith("## "):
            story.append(Paragraph(esc(stripped[3:].strip()), styles["h2"]))
            i += 1
            continue

        if stripped.startswith(">"):
            story.append(Paragraph(esc(stripped.lstrip("> ").strip()), styles["quote"]))
            i += 1
            continue

        if stripped.startswith("- "):
            story.append(Paragraph("- " + esc(stripped[2:].strip()), styles["bullet"]))
            i += 1
            continue

        paragraph = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt or nxt.startswith("#") or nxt.startswith("|") or nxt.startswith(">") or nxt.startswith("- "):
                break
            paragraph.append(nxt)
            i += 1
        story.append(Paragraph(esc(" ".join(paragraph)), styles["subtitle" if len(story) == 1 else "body"]))

    return story


def draw_page(canvas, doc):
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(colors.HexColor("#103f4a"))
    canvas.rect(0, height - 0.42 * inch, width, 0.42 * inch, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("NotoSC", 8)
    canvas.drawString(0.72 * inch, height - 0.27 * inch, doc.proposal_header)
    canvas.setFillColor(colors.HexColor("#6f7f86"))
    canvas.drawString(0.72 * inch, 0.38 * inch, "Prepared for early MVP validation, subscription app planning, and startup exploration")
    canvas.drawRightString(width - 0.72 * inch, 0.38 * inch, f"Page {doc.page}")
    canvas.restoreState()


def main():
    parser = argparse.ArgumentParser(description="Build a proposal PDF from a simple Markdown source.")
    parser.add_argument("source", nargs="?", default="canine_resting_vitals_smart_collar_proposal_v3_delta_first.md")
    parser.add_argument("output", nargs="?", default=None)
    parser.add_argument("--header", default="Canine Resting Vitals Smart Collar - Proposal")
    parser.add_argument("--title", default="Canine Resting Vitals Smart Collar Proposal")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.is_absolute():
        source = ROOT / source
    output = Path(args.output) if args.output else source.with_suffix(".pdf")
    if not output.is_absolute():
        output = ROOT / output

    register_fonts()
    styles = make_styles()
    markdown = source.read_text(encoding="utf-8")
    story = build_story(markdown, styles)

    doc = BaseDocTemplate(
        str(output),
        pagesize=letter,
        leftMargin=0.68 * inch,
        rightMargin=0.68 * inch,
        topMargin=0.78 * inch,
        bottomMargin=0.68 * inch,
        title=args.title,
        author="Codex",
    )
    doc.proposal_header = args.header
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="proposal", frames=[frame], onPage=draw_page)])
    doc.build(story)
    print(output)


if __name__ == "__main__":
    main()
