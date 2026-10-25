"""Sutra Regulatory Gap Analysis Engine & PDF Report Generator.
Traceability: REQ-5.1, REQ-5.2, REQ-5.3, REQ-5.4, REQ-5.5, REQ-5.6
"""

import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from services.common.models import (
    AIModel,
    ExposureProfile,
    Finding,
    FindingStatus,
    GapReport,
    PolicyDocument,
    RegChunk,
    RiskTier,
)
from services.rag.judges import OfflineJudge
from services.rag.policy_extractor import PolicyExtractor

DISCLAIMER = "Decision-support information only; not legal advice."


class GapAnalysisEngine:
    """Core contribution: Framework-aware, tier-filtered gap analysis engine."""

    def __init__(self):
        self.extractor = PolicyExtractor()
        self.judge = OfflineJudge()

    def run_gap_analysis(
        self,
        db: Session,
        model_id: str,
        policy_document_id: str,
        exposure_profile: ExposureProfile,
    ) -> GapReport:
        """Execute automated framework-aware, tier-filtered gap analysis.
        Traceability: REQ-5.1, REQ-5.2, REQ-5.3, REQ-5.4, REQ-5.5
        """
        model = db.query(AIModel).filter(AIModel.id == model_id).first()
        if not model:
            raise ValueError(f"AI Model {model_id} not found.")

        policy_doc = db.query(PolicyDocument).filter(PolicyDocument.id == policy_document_id).first()
        if not policy_doc:
            raise ValueError(f"Policy Document {policy_document_id} not found.")

        # 1. Extract sections from policy
        policy_text = policy_doc.storage_key  # Contains text or file path
        # If storage_key is plain text, use it; else read file
        import os
        if os.path.exists(policy_text):
            policy_bytes = open(policy_text, "rb").read()
            sections = self.extractor.extract(policy_bytes, policy_doc.filename)
        else:
            sections = self.extractor.extract_from_text(policy_text, policy_doc.filename)

        # 2. Filter obligations by model tier and exposure profile (REQ-5.2)
        active_frameworks = ["india"]
        if exposure_profile == ExposureProfile.INDIA_PLUS_EU:
            active_frameworks.append("eu")

        model_tier_str = model.current_tier.value.lower()

        chunks = db.query(RegChunk).all()
        target_obligations: List[RegChunk] = []

        for chunk in chunks:
            chunk_frameworks = chunk.frameworks if isinstance(chunk.frameworks, list) else []
            chunk_tiers = [t.lower() for t in (chunk.tiers if isinstance(chunk.tiers, list) else [])]

            if any(f in active_frameworks for f in chunk_frameworks) and model_tier_str in chunk_tiers:
                target_obligations.append(chunk)

        if not target_obligations:
            # Fallback if no specific tier matches: include all matching active frameworks
            target_obligations = [c for c in chunks if any(f in active_frameworks for f in (c.frameworks or []))]

        # 3. Create GapReport record
        report = GapReport(
            model_id=model.id,
            policy_document_id=policy_doc.id,
            exposure_profile=exposure_profile,
            tier=model.current_tier,
            summary={},
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # 4. Evaluate each obligation against policy using Compliance Judge
        covered_count = 0
        partial_count = 0
        gap_count = 0
        instrument_stats: Dict[str, Dict[str, int]] = {}

        for ob in target_obligations:
            ob_dict = {
                "instrument": ob.instrument,
                "section_id": ob.section_id,
                "text": ob.text,
            }
            eval_res = self.judge.evaluate(ob_dict, sections)
            status = eval_res["status"]

            if status == FindingStatus.COVERED:
                covered_count += 1
            elif status == FindingStatus.PARTIALLY_COVERED:
                partial_count += 1
            else:
                gap_count += 1

            # Stats by instrument
            inst = ob.instrument
            if inst not in instrument_stats:
                instrument_stats[inst] = {"covered": 0, "partially_covered": 0, "gap": 0, "total": 0}
            instrument_stats[inst]["total"] += 1
            instrument_stats[inst][status.value] += 1

            finding = Finding(
                report_id=report.id,
                chunk_id=ob.id,
                obligation_summary=ob.text.splitlines()[0] if ob.text else ob.section_id,
                status=status,
                evidence_excerpt=eval_res["evidence_excerpt"] or "[No evidence identified in policy]",
                policy_location=eval_res["policy_location"],
                cited_instrument=ob.instrument,
                cited_section=ob.section_id,
                remediation_note=eval_res["remediation_note"],
                confidence=eval_res["confidence"],
            )
            db.add(finding)

        total_obs = max(len(target_obligations), 1)
        coverage_pct = round(((covered_count + (0.5 * partial_count)) / total_obs) * 100, 1)

        report.summary = {
            "total_obligations": len(target_obligations),
            "covered": covered_count,
            "partially_covered": partial_count,
            "gap": gap_count,
            "coverage_percentage": coverage_pct,
            "instrument_breakdown": instrument_stats,
            "disclaimer": DISCLAIMER,
        }
        db.commit()
        db.refresh(report)
        return report

    def generate_pdf_report(self, db: Session, report_id: str) -> bytes:
        """Generate high-fidelity PDF report with legal disclaimer banner using ReportLab.
        Traceability: REQ-5.5
        """
        report = db.query(GapReport).filter(GapReport.id == report_id).first()
        if not report:
            raise ValueError(f"GapReport {report_id} not found.")

        findings = db.query(Finding).filter(Finding.report_id == report_id).all()
        model = db.query(AIModel).filter(AIModel.id == report.model_id).first()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1e293b"),
        )
        disclaimer_style = ParagraphStyle(
            "DisclaimerBanner",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#991b1b"),
            backColor=colors.HexColor("#fee2e2"),
            borderPadding=8,
            alignment=1,
        )
        body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=12)
        bold_style = ParagraphStyle("Bold", parent=styles["Normal"], fontSize=9, leading=12, fontName="Helvetica-Bold")

        story = []

        # 1. Header Title
        story.append(Paragraph("Sutra AI Governance & Compliance Intelligence", title_style))
        story.append(Paragraph("Automated Regulatory Gap Analysis Report", styles["Heading3"]))
        story.append(Spacer(1, 10))

        # 2. Mandatory Legal Disclaimer Banner
        story.append(Paragraph(f"<b>LEGAL DISCLAIMER:</b> {DISCLAIMER}", disclaimer_style))
        story.append(Spacer(1, 15))

        # 3. Model & Audit Metadata Table
        model_name = model.name if model else "Unknown Model"
        summary = report.summary or {}
        meta_data = [
            [Paragraph("Target Model:", bold_style), Paragraph(model_name, body_style), Paragraph("Evaluation Date:", bold_style), Paragraph(str(report.created_at)[:19], body_style)],
            [Paragraph("Risk Tier:", bold_style), Paragraph(report.tier.value.upper(), body_style), Paragraph("Exposure Profile:", bold_style), Paragraph(report.exposure_profile.value.replace("_", " ").title(), body_style)],
            [Paragraph("Total Obligations:", bold_style), Paragraph(str(summary.get("total_obligations", 0)), body_style), Paragraph("Coverage Score:", bold_style), Paragraph(f"{summary.get('coverage_percentage', 0)}%", bold_style)],
        ]
        meta_table = Table(meta_data, colWidths=[110, 150, 110, 150])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 15))

        # 4. Summary Score Card
        summary_data = [
            [Paragraph("Status", bold_style), Paragraph("Count", bold_style), Paragraph("Percentage", bold_style)],
            [Paragraph("Covered", body_style), Paragraph(str(summary.get("covered", 0)), body_style), Paragraph(f"{round((summary.get('covered', 0)/max(summary.get('total_obligations', 1), 1))*100, 1)}%", body_style)],
            [Paragraph("Partially Covered", body_style), Paragraph(str(summary.get("partially_covered", 0)), body_style), Paragraph(f"{round((summary.get('partially_covered', 0)/max(summary.get('total_obligations', 1), 1))*100, 1)}%", body_style)],
            [Paragraph("Compliance Gap", body_style), Paragraph(str(summary.get("gap", 0)), body_style), Paragraph(f"{round((summary.get('gap', 0)/max(summary.get('total_obligations', 1), 1))*100, 1)}%", body_style)],
        ]
        sum_table = Table(summary_data, colWidths=[180, 170, 170])
        sum_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(sum_table)
        story.append(Spacer(1, 20))

        # 5. Detailed Findings Table
        story.append(Paragraph("Statutory Findings & Remediation Advisory", styles["Heading3"]))
        story.append(Spacer(1, 8))

        findings_data = [
            [Paragraph("Instrument & Section", bold_style), Paragraph("Status", bold_style), Paragraph("Remediation Advisory Note", bold_style)]
        ]

        for f in findings:
            status_color = "#16a34a" if f.status == FindingStatus.COVERED else ("#d97706" if f.status == FindingStatus.PARTIALLY_COVERED else "#dc2626")
            status_p = Paragraph(f"<font color='{status_color}'><b>{f.status.value.upper()}</b></font>", body_style)
            inst_p = Paragraph(f"<b>{f.cited_instrument}</b><br/>{f.cited_section}", body_style)
            rem_p = Paragraph(f.remediation_note or "Compliant", body_style)
            findings_data.append([inst_p, status_p, rem_p])

        findings_table = Table(findings_data, colWidths=[150, 90, 280])
        findings_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(findings_table)

        doc.build(story)
        return buffer.getvalue()
