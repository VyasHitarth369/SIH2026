"""mou_generator.py

Authoritative PDF Generator for VidySetu Tripartite Memorandum of Understanding (MOU).
Generates compliant binary PDF documents using ReportLab with official institutional
disclaimers, tripartite signatory blocks, and project terms.
"""

import io
from typing import Any, Dict, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)


def generate_mou_pdf(project_data: Dict[str, Any]) -> bytes:
    """Generates an official VidySetu Tripartite Memorandum of Understanding PDF document.

    Returns raw PDF bytes starting with %PDF-.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_gov = ParagraphStyle(
        "GovTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        alignment=1,  # Center
        textColor=colors.HexColor("#1E3A8A"),
    )

    subtitle_dept = ParagraphStyle(
        "DeptSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        alignment=1,
        textColor=colors.HexColor("#475569"),
    )

    mou_heading = ParagraphStyle(
        "MOUHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        alignment=1,
        textColor=colors.HexColor("#0F172A"),
    )

    draft_badge = ParagraphStyle(
        "DraftBadge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        alignment=1,
        textColor=colors.HexColor("#B45309"),
    )

    agreement_sub = ParagraphStyle(
        "AgreementSub",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        alignment=1,
        textColor=colors.HexColor("#2563EB"),
    )

    disclaimer_text = ParagraphStyle(
        "DisclaimerText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#92400E"),
    )

    body_text = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1E293B"),
    )

    body_bold = ParagraphStyle(
        "BodyBoldCustom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#0F172A"),
    )

    clause_title = ParagraphStyle(
        "ClauseTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0F172A"),
    )

    signatory_title = ParagraphStyle(
        "SignTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=colors.HexColor("#0F172A"),
    )

    signatory_role = ParagraphStyle(
        "SignRole",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        alignment=1,
        textColor=colors.HexColor("#64748B"),
    )

    project_id = project_data.get("project_id", "PRJ-UNKNOWN")
    project_title = project_data.get("project_title") or project_data.get("title") or "Collaborative Innovation Project"
    project_desc = project_data.get("description") or "Applied collaborative research and prototype development."
    uni_name = project_data.get("university_name") or "Participating Academic Institution"
    uni_id = project_data.get("university_id") or "U-STATE"
    ind_name = project_data.get("industry_name") or "Industrial Partner Organization"
    ind_id = project_data.get("industry_id") or "I-PARTNER"
    effective_date = project_data.get("effective_date") or project_data.get("start_date") or "Current Academic Session"

    story = []

    # 1. State Header
    story.append(Paragraph("GOVERNMENT OF JHARKHAND", title_gov))
    story.append(Spacer(1, 2))
    story.append(Paragraph("Department of Higher & Technical Education", subtitle_dept))
    story.append(Spacer(1, 6))
    story.append(Paragraph("MEMORANDUM OF UNDERSTANDING", mou_heading))
    story.append(Spacer(1, 2))
    story.append(Paragraph("VidySetu MOU Draft / Template", draft_badge))
    story.append(Spacer(1, 2))
    story.append(Paragraph("VidySetu Tripartite Innovation & Research Collaborative Agreement", agreement_sub))
    story.append(Spacer(1, 8))

    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceBefore=2, spaceAfter=8))

    # 2. Institutional Disclaimer Box
    disclaimer_html = (
        "<b>DRAFT TEMPLATE — FOR INSTITUTIONAL REVIEW ONLY:</b> "
        "This document serves as an institutional preview and draft template for collaborative alignment. "
        "It is NOT an executed legal instrument until formally signed by all three authorized signatories "
        "and uploaded to the secure VidySetu repository."
    )
    disclaimer_table = Table(
        [[Paragraph(disclaimer_html, disclaimer_text)]],
        colWidths=[530],
    )
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FCD34D")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(disclaimer_table)
    story.append(Spacer(1, 10))

    # 3. Tripartite Parties
    parties_intro = (
        f"This Memorandum of Understanding is entered into as of <b>{effective_date}</b> by and between:"
    )
    story.append(Paragraph(parties_intro, body_text))
    story.append(Spacer(1, 6))

    parties_table_data = [
        [
            Paragraph("<b>Party 1 (Government Authority):</b>", body_bold),
            Paragraph("Department of Higher & Technical Education, Government of Jharkhand.", body_text),
        ],
        [
            Paragraph("<b>Party 2 (Academic Institution):</b>", body_bold),
            Paragraph(f"<b>{uni_name}</b> (Institution ID: {uni_id}).", body_text),
        ],
        [
            Paragraph("<b>Party 3 (Industrial Partner):</b>", body_bold),
            Paragraph(f"<b>{ind_name}</b> (Industry ID: {ind_id}).", body_text),
        ],
    ]
    parties_table = Table(parties_table_data, colWidths=[180, 350])
    parties_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 10))

    # 4. Project Reference Box
    proj_table_data = [
        [Paragraph("<b>COLLABORATIVE PROJECT STATEMENT</b>", ParagraphStyle("H", parent=body_bold, fontSize=8.5, textColor=colors.HexColor("#475569")))],
        [Paragraph(f"<b>Project Title:</b> {project_title}", body_bold)],
        [Paragraph(f"<b>Reference ID:</b> {project_id}", ParagraphStyle("Ref", parent=body_text, fontSize=8.5, textColor=colors.HexColor("#64748B")))],
        [Paragraph(f"<b>Scope & Purpose:</b> {project_desc}", body_text)],
    ]
    proj_table = Table(proj_table_data, colWidths=[530])
    proj_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
    ]))
    story.append(proj_table)
    story.append(Spacer(1, 10))

    # 5. Formal Collaboration Terms & Clauses
    story.append(Paragraph("Key Collaboration Terms:", clause_title))
    story.append(Spacer(1, 4))

    clauses = [
        ("1. Scope & Objective", "Development, prototyping, and deployment of field-tested solutions for verified regional civic challenges."),
        ("2. Student & Faculty Engagement", "Academic guides and student researchers shall receive institutional resources, direct industry mentorship, and academic credit."),
        ("3. Industry Participation", "Industrial mentors shall provide technical guidance, testing infrastructure, and potential CSR/deployment grants upon pilot validation."),
        ("4. Government Monitoring", "All progress milestones, impact metrics, and final deployment outcomes shall be tracked authoritatively on the VidySetu state platform."),
    ]
    clause_rows = []
    for c_title, c_desc in clauses:
        clause_rows.append([
            Paragraph(f"<b>{c_title}:</b>", body_bold),
            Paragraph(c_desc, body_text),
        ])
    clauses_table = Table(clause_rows, colWidths=[160, 370])
    clauses_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(clauses_table)
    story.append(Spacer(1, 16))

    # 6. Formal Signatory Blocks (3 Columns)
    sign_table_data = [
        [
            Paragraph("____________________________<br/><b>For Government of Jharkhand</b>", signatory_title),
            Paragraph(f"____________________________<br/><b>For {uni_name}</b>", signatory_title),
            Paragraph(f"____________________________<br/><b>For {ind_name}</b>", signatory_title),
        ],
        [
            Paragraph("Authorized Officer<br/>Dept of Higher & Technical Education", signatory_role),
            Paragraph("Dean / Registrar (Academic)<br/>Authorized Signatory", signatory_role),
            Paragraph("Authorized Director / SPOC<br/>Industry Partner Organization", signatory_role),
        ],
    ]
    sign_table = Table(sign_table_data, colWidths=[176, 176, 176])
    sign_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(KeepTogether(sign_table))

    doc.build(story)
    return buffer.getvalue()
