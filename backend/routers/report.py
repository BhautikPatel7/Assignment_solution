"""
report.py — Module 5.8: PDF Report Generation Router

GET /api/report/{session_id}
  Input:  session_id
  Flow:
    1. Load session → get original_image, composite_image, material_selections, estimate_data
    2. Generate PDF using reportlab
  Output: PDF FileResponse
"""

import os
import base64
from io import BytesIO
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

from config import logger
from utils import load_session, session_exists

router = APIRouter()

def create_pdf(session_id: str, session: dict) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=18
    )
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1  # Center
    
    normal_style = styles['Normal']
    
    elements = []
    
    # 1. Header
    elements.append(Paragraph(f"E2M Renovation Estimate Report", title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Session ID:</b> {session_id}", normal_style))
    elements.append(Spacer(1, 20))
    
    # 2. Images (Before & After)
    seg_data = session.get("segmentation_data", {})
    viz_img_b64 = session.get("composite_image")
    orig_img_b64 = seg_data.get("original_image")
    
    if orig_img_b64 and viz_img_b64:
        try:
            orig_bytes = base64.b64decode(orig_img_b64)
            viz_bytes = base64.b64decode(viz_img_b64)
            
            orig_reader = ImageReader(BytesIO(orig_bytes))
            viz_reader = ImageReader(BytesIO(viz_bytes))
            
            orig_img = Image(orig_reader, width=220, height=150)
            viz_img = Image(viz_reader, width=220, height=150)
            
            img_table = Table([[orig_img, viz_img]], colWidths=[240, 240])
            img_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(img_table)
            
            label_table = Table([["Original", "AI Visualization"]], colWidths=[240, 240])
            label_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(label_table)
            elements.append(Spacer(1, 20))
        except Exception as e:
            logger.error(f"Error processing images for PDF: {e}")
            
    # 3. Materials
    selections = session.get("material_selections", {})
    if selections:
        elements.append(Paragraph("Selected Materials", styles['Heading2']))
        mat_data = [["Region", "Material"]]
        for region, sel in selections.items():
            region_name = region.replace('_', ' ').title()
            val = sel.get("value", "")
            mat_data.append([region_name, val])
            
        mat_table = Table(mat_data, colWidths=[200, 300])
        mat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(mat_table)
        elements.append(Spacer(1, 20))

    # 4. Estimate Breakdown
    est_data = session.get("estimate_data", {})
    breakdown = est_data.get("breakdown", [])
    summary = est_data.get("summary", {})
    
    if breakdown:
        elements.append(Paragraph("Cost Estimate Breakdown", styles['Heading2']))
        est_table_data = [["Region", "Material", "Qty", "Mat. Cost", "Labor Cost", "Total"]]
        
        for item in breakdown:
            region = item.get("region", "").replace('_', ' ').title()
            material = item.get("material", "")
            qty = f"{item.get('quantity_needed', 0):.1f} {item.get('unit', '')}"
            m_cost = f"INR {item.get('material_cost', 0):.0f}"
            l_cost = f"INR {item.get('labor_cost', 0):.0f}"
            t_cost = f"INR {item.get('total_cost', 0):.0f}"
            est_table_data.append([region, material, qty, m_cost, l_cost, t_cost])
            
        est_table = Table(est_table_data, colWidths=[100, 100, 60, 80, 80, 80])
        est_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(est_table)
        elements.append(Spacer(1, 20))
        
    if summary:
        elements.append(Paragraph(f"<b>Total Materials:</b> INR {summary.get('total_material_cost', 0):.0f}", normal_style))
        elements.append(Spacer(1, 5))
        elements.append(Paragraph(f"<b>Total Labor:</b> INR {summary.get('total_labor_cost', 0):.0f}", normal_style))
        elements.append(Spacer(1, 5))
        elements.append(Paragraph(f"<b>Grand Total:</b> INR {summary.get('grand_total', 0):.0f}", styles['Heading3']))
        elements.append(Spacer(1, 20))

    # Disclaimer
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray,
        fontName='Helvetica-Oblique'
    )
    elements.append(Paragraph("* This is an AI-generated estimate based on image dimensions and standard local rates.", disclaimer_style))
    elements.append(Paragraph("* Actual site conditions may vary. Please consult a professional for an exact quote.", disclaimer_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

@router.get("/api/report/{session_id}")
async def download_report(session_id: str):
    """
    Generate and download the PDF report.
    """
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = load_session(session_id)
    
    try:
        pdf_buffer = create_pdf(session_id, session)
        return StreamingResponse(
            pdf_buffer, 
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Estimate_Report_{session_id[:8]}.pdf"}
        )
    except Exception as e:
        logger.error(f"[{session_id}] Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
