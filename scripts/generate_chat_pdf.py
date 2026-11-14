"""
ASTRA SENSE – ORBITAL GUARD
Complete Chat History & Trajectory Transcript PDF Generator
Generates a comprehensive, professional PDF documenting the full conversation history.
"""

import os
import sys
import json
import re
import html
from pathlib import Path
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable
)
from reportlab.pdfgen import canvas

# ==============================================================================
# Numbered Canvas for "Page X of Y" and Running Header/Footer
# ==============================================================================
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Don't draw running header on cover page
        if self._pageNumber > 1:
            # Running Header
            self.drawString(36, letter[1] - 28, "ASTRA SENSE – ORBITAL GUARD  |  Complete Chat History & Trajectory Transcript")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(36, letter[1] - 32, letter[0] - 36, letter[1] - 32)
        
        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 36, letter[0] - 36, 36)
        
        timestamp_str = "November 13, 2026  •  Mission Elapsed Trajectory  •  Phase 1, 2 & 2.5"
        self.drawString(36, 24, timestamp_str)
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(letter[0] - 36, 24, page_str)
        self.restoreState()


# ==============================================================================
# Markdown to Flowables Parsing Engine
# ==============================================================================
def sanitize_text(text: str) -> str:
    """Escapes XML entities while converting markdown bold, and code."""
    if not text:
        return ""
    # Strip user request tags
    text = text.replace("<USER_REQUEST>", "").replace("</USER_REQUEST>", "")
    
    # Escape XML first
    text = html.escape(text)
    
    # Convert inline code `code` to monospaced font
    text = re.sub(r'`([^`]+)`', r'<font face="Courier" color="#0369A1"><b>\1</b></font>', text)
    # Convert bold **text** to <b>text</b>
    text = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', text)
    
    return text

def make_safe_paragraph(text: str, style: ParagraphStyle, raw_fallback: str) -> Paragraph:
    """Safely constructs a Paragraph with graceful fallback to plain escaped text if parsing fails."""
    try:
        return Paragraph(text, style)
    except Exception:
        safe_fallback = html.escape(raw_fallback.replace("<USER_REQUEST>", "").replace("</USER_REQUEST>", ""))
        return Paragraph(safe_fallback, style)

def create_code_block(code_text: str, lang: str, styles: dict):
    """Wraps preformatted code into an elegant styled callout table."""
    safe_code = html.escape(code_text)
    code_lines = safe_code.split("\n")
    # Truncate lines that are exceptionally long to avoid page clipping
    truncated_lines = [l[:130] for l in code_lines]
    formatted_code = "<br/>".join(truncated_lines) if truncated_lines else "&nbsp;"
    
    p = Paragraph(f'<font face="Courier" size="7" color="#1E293B">{formatted_code}</font>', styles["CodeText"])
    
    table = Table([[p]], colWidths=[letter[0] - 72])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return table

def create_markdown_table(table_lines: list, styles: dict):
    """Converts markdown table lines into a clean ReportLab Table."""
    try:
        data = []
        is_header = True
        
        for line in table_lines:
            stripped = line.strip()
            # Skip separator line |:---|:---|
            if re.match(r'^\|[\s\:\-]+(\/[\s\:\-]+)*\|$', stripped) or "---" in stripped:
                continue
                
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            row_data = []
            for c in cells:
                safe_c = sanitize_text(c)
                style = styles["TableHeader"] if is_header else styles["TableCell"]
                row_data.append(make_safe_paragraph(safe_c, style, c))
            data.append(row_data)
            is_header = False
            
        if not data or not data[0]:
            return None
            
        num_cols = len(data[0])
        avail_width = letter[0] - 72
        col_w = avail_width / num_cols
        
        # Normalize row lengths
        normalized_data = []
        for r in data:
            if len(r) < num_cols:
                r.extend([Paragraph("", styles["TableCell"])] * (num_cols - len(r)))
            normalized_data.append(r[:num_cols])
            
        t = Table(normalized_data, colWidths=[col_w] * num_cols)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        return t
    except Exception:
        # Fallback to plain code block representation
        return create_code_block("\n".join(table_lines), "", styles)

def parse_markdown_to_flowables(raw_text: str, styles: dict, is_user: bool = False):
    """Parses raw message markdown into structured ReportLab flowables."""
    flowables = []
    lines = raw_text.replace("\r\n", "\n").split("\n")
    
    in_code_block = False
    code_lines = []
    code_lang = ""
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Handle code block toggles
        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lang = stripped[3:].strip()
                code_lines = []
            else:
                in_code_block = False
                code_text = "\n".join(code_lines)
                code_flowable = create_code_block(code_text, code_lang, styles)
                flowables.append(code_flowable)
                flowables.append(Spacer(1, 4))
            i += 1
            continue
            
        if in_code_block:
            code_lines.append(line)
            i += 1
            continue
            
        # Empty lines
        if not stripped:
            flowables.append(Spacer(1, 3))
            i += 1
            continue
            
        # Handle markdown tables
        if stripped.startswith("|") and stripped.endswith("|"):
            tbl_lines = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                tbl_lines.append(lines[i].strip())
                i += 1
            tbl_flowable = create_markdown_table(tbl_lines, styles)
            if tbl_flowable:
                flowables.append(tbl_flowable)
                flowables.append(Spacer(1, 4))
            continue

        # Horizontal rules
        if stripped in ("---", "***", "___", "===", "=================================================="):
            flowables.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=4, spaceAfter=4))
            i += 1
            continue
            
        # Headings
        if stripped.startswith("# "):
            h_text = sanitize_text(stripped[2:])
            flowables.append(make_safe_paragraph(h_text, styles["DocHeading1"], stripped[2:]))
            flowables.append(Spacer(1, 4))
            i += 1
            continue
        elif stripped.startswith("## "):
            h_text = sanitize_text(stripped[3:])
            flowables.append(make_safe_paragraph(h_text, styles["DocHeading2"], stripped[3:]))
            flowables.append(Spacer(1, 3))
            i += 1
            continue
        elif stripped.startswith("### "):
            h_text = sanitize_text(stripped[4:])
            flowables.append(make_safe_paragraph(h_text, styles["DocHeading3"], stripped[4:]))
            flowables.append(Spacer(1, 2))
            i += 1
            continue
        elif stripped.startswith("#### "):
            h_text = sanitize_text(stripped[5:])
            flowables.append(make_safe_paragraph(h_text, styles["DocHeading4"], stripped[5:]))
            flowables.append(Spacer(1, 2))
            i += 1
            continue
            
        # Bullet list items
        if stripped.startswith(("- ", "* ", "• ")):
            bullet_text = sanitize_text(stripped[2:])
            flowables.append(make_safe_paragraph(f"• &nbsp; {bullet_text}", styles["DocBullet"], stripped))
            i += 1
            continue
            
        # Numbered list items
        num_match = re.match(r'^(\d+)\.\s+(.+)$', stripped)
        if num_match:
            num = num_match.group(1)
            item_text = sanitize_text(num_match.group(2))
            flowables.append(make_safe_paragraph(f"<b>{num}.</b> &nbsp; {item_text}", styles["DocBullet"], stripped))
            i += 1
            continue
            
        # Blockquotes
        if stripped.startswith("> "):
            quote_text = sanitize_text(stripped[2:])
            flowables.append(make_safe_paragraph(quote_text, styles["DocBlockquote"], stripped[2:]))
            flowables.append(Spacer(1, 2))
            i += 1
            continue
            
        # Standard paragraph text
        p_text = sanitize_text(line)
        style = styles["UserBody"] if is_user else styles["DocBody"]
        flowables.append(make_safe_paragraph(p_text, style, line))
        flowables.append(Spacer(1, 2))
        i += 1

    return flowables


# ==============================================================================
# Main PDF Builder Function
# ==============================================================================
def build_chat_history_pdf(transcript_path: Path, output_path: Path):
    print(f"Loading transcript from: {transcript_path}")
    
    dialogue = []
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            t = data.get('type')
            c = data.get('content')
            if t in ('USER_INPUT', 'PLANNER_RESPONSE') and c:
                role = 'USER' if t == 'USER_INPUT' else 'ASSISTANT'
                dialogue.append({
                    'role': role,
                    'step': data.get('step_index', 0),
                    'timestamp': data.get('created_at', ''),
                    'content': c
                })
                
    print(f"Extracted {len(dialogue)} total dialogue turns.")

    # Setup styles
    sample_styles = getSampleStyleSheet()
    
    styles = {
        "CoverTitle": ParagraphStyle(
            "CoverTitle",
            parent=sample_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0F172A"),
            alignment=0,
            spaceAfter=4
        ),
        "CoverSubtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#0284C7"),
            spaceAfter=10
        ),
        "CoverMeta": ParagraphStyle(
            "CoverMeta",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#475569")
        ),
        "TurnHeaderUser": ParagraphStyle(
            "TurnHeaderUser",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#0369A1")
        ),
        "TurnHeaderAssistant": ParagraphStyle(
            "TurnHeaderAssistant",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#0D9488")
        ),
        "DocHeading1": ParagraphStyle(
            "DocHeading1",
            parent=sample_styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=6,
            spaceAfter=3
        ),
        "DocHeading2": ParagraphStyle(
            "DocHeading2",
            parent=sample_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=4,
            spaceAfter=2
        ),
        "DocHeading3": ParagraphStyle(
            "DocHeading3",
            parent=sample_styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#334155"),
            spaceBefore=3,
            spaceAfter=2
        ),
        "DocHeading4": ParagraphStyle(
            "DocHeading4",
            parent=sample_styles["Heading4"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#475569"),
            spaceBefore=2,
            spaceAfter=1
        ),
        "DocBody": ParagraphStyle(
            "DocBody",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1E293B")
        ),
        "UserBody": ParagraphStyle(
            "UserBody",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0F172A")
        ),
        "DocBullet": ParagraphStyle(
            "DocBullet",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            leftIndent=10,
            textColor=colors.HexColor("#1E293B")
        ),
        "DocBlockquote": ParagraphStyle(
            "DocBlockquote",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10.5,
            leftIndent=12,
            textColor=colors.HexColor("#475569")
        ),
        "CodeText": ParagraphStyle(
            "CodeText",
            parent=sample_styles["Normal"],
            fontName="Courier",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#0F172A")
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=sample_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#0F172A")
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#1E293B")
        )
    }

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=38,
        bottomMargin=38
    )

    story = []

    # =========================================================================
    # Cover / Header Banner
    # =========================================================================
    story.append(Paragraph("ASTRA SENSE – ORBITAL GUARD", styles["CoverTitle"]))
    story.append(Paragraph("Complete Engineering Chat History & Mission Trajectory Transcript", styles["CoverSubtitle"]))
    
    meta_table_data = [
        [
            Paragraph("<b>Target Architecture:</b> React 19 + FastAPI + SQLite WAL + Supabase", styles["CoverMeta"]),
            Paragraph(f"<b>Total Messages:</b> {len(dialogue)} Dialogue Turns", styles["CoverMeta"])
        ],
        [
            Paragraph("<b>Mission Phases:</b> Phase 1, Phase 2, Phase 2.5 Live Acceptance", styles["CoverMeta"]),
            Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y - %H:%M:%S')} UTC", styles["CoverMeta"])
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[letter[0]/2 - 36, letter[0]/2 - 36])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceBefore=2, spaceAfter=10))

    # =========================================================================
    # Dialogue Turns
    # =========================================================================
    for idx, turn in enumerate(dialogue):
        is_user = turn["role"] == "USER"
        turn_num = idx + 1
        role_label = "USER PROMPT" if is_user else "ANTIGRAVITY RESPONSE"
        timestamp = turn["timestamp"]
        step = turn["step"]
        
        # Turn Banner Header
        header_text = f"<b>TURN {turn_num}  |  {role_label}</b>  •  Step {step}  •  {timestamp}"
        h_style = styles["TurnHeaderUser"] if is_user else styles["TurnHeaderAssistant"]
        header_p = make_safe_paragraph(header_text, h_style, f"TURN {turn_num} | {role_label}")
        
        banner_table = Table([[header_p]], colWidths=[letter[0] - 72])
        bg_color = colors.HexColor("#E0F2FE") if is_user else colors.HexColor("#F0FDF4")
        border_color = colors.HexColor("#0284C7") if is_user else colors.HexColor("#10B981")
        
        banner_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('BOX', (0, 0), (-1, -1), 0.75, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(banner_table)
        story.append(Spacer(1, 4))
        
        # Content Flowables
        content_flowables = parse_markdown_to_flowables(turn["content"], styles, is_user=is_user)
        for cf in content_flowables:
            story.append(cf)
            
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceBefore=2, spaceAfter=8))

    print("Building PDF document...")
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated at: {output_path}")
    print(f"File size: {output_path.stat().st_size} bytes")

if __name__ == "__main__":
    t_path = Path(r"C:\Users\jadha\.gemini\antigravity\brain\f643ab73-3fad-45b6-b60e-c67226e54f1b\.system_generated\logs\transcript_full.jsonl")
    out_pdf = Path(r"d:\ASTRA-SENSE-ORBITAL-GUARD\ASTRA_SENSE_COMPLETE_CHAT_HISTORY.pdf")
    build_chat_history_pdf(t_path, out_pdf)
