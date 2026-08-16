import jsPDF from 'jspdf';
import 'jspdf-autotable';
import { isPaint } from '../constants/materials';

export async function generateReportPDF({ session, segData, vizData, estData }) {
  const doc = new jsPDF({ format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();

  // Helper to center text
  const centerText = (text, y, size = 12) => {
    doc.setFontSize(size);
    const textWidth = doc.getTextWidth(text);
    doc.text(text, (pageWidth - textWidth) / 2, y);
  };

  // 1. Header
  doc.setFont("helvetica", "bold");
  centerText("E2M Renovation Estimate Report", 20, 20);
  
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.text(`Session ID: ${session.session_id}`, 15, 30);
  doc.text(`Date: ${new Date().toLocaleDateString()}`, pageWidth - 15, 30, { align: "right" });

  doc.line(15, 35, pageWidth - 15, 35);

  let cursorY = 45;

  // 2. Images
  if (segData?.original_image && vizData?.visualization_image) {
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text("Before & After Comparison", 15, cursorY);
    cursorY += 10;

    const imgWidth = 85;
    const imgHeight = 60; // Assuming ~4:3 aspect ratio
    
    // Before Image
    doc.addImage(`data:image/jpeg;base64,${segData.original_image}`, 'JPEG', 15, cursorY, imgWidth, imgHeight);
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.text("Original", 15 + (imgWidth/2), cursorY + imgHeight + 5, { align: 'center' });

    // After Image
    doc.addImage(`data:image/jpeg;base64,${vizData.visualization_image}`, 'JPEG', pageWidth - 15 - imgWidth, cursorY, imgWidth, imgHeight);
    doc.text("AI Visualization", pageWidth - 15 - (imgWidth/2), cursorY + imgHeight + 5, { align: 'center' });

    cursorY += imgHeight + 15;
  }

  // 3. Selected Materials
  if (vizData?.selections) {
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text("Selected Materials", 15, cursorY);
    cursorY += 8;

    const matRows = Object.entries(vizData.selections).map(([rid, sel]) => {
      const region = rid.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
      const value = isPaint(sel.value) ? `Paint (${sel.value})` : `Texture (${sel.value})`;
      return [region, value];
    });

    doc.autoTable({
      startY: cursorY,
      head: [['Region', 'Material']],
      body: matRows,
      margin: { left: 15, right: 15 },
      theme: 'grid',
      headStyles: { fillColor: [40, 40, 40] }
    });

    cursorY = doc.lastAutoTable.finalY + 15;
  }

  // Check page break
  if (cursorY > 250) {
    doc.addPage();
    cursorY = 20;
  }

  // 4. Estimate Breakdown
  if (estData?.data?.breakdown) {
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text("Cost Estimate Breakdown", 15, cursorY);
    cursorY += 8;

    const breakdownRows = estData.data.breakdown.map(item => [
      item.region.replace('_', ' ').toUpperCase(),
      item.material,
      `${item.quantity_needed.toFixed(1)} ${item.unit}`,
      `₹${item.material_cost.toFixed(0)}`,
      `₹${item.labor_cost.toFixed(0)}`,
      `₹${item.total_cost.toFixed(0)}`
    ]);

    doc.autoTable({
      startY: cursorY,
      head: [['Region', 'Material', 'Quantity', 'Mat. Cost', 'Labor Cost', 'Total Cost']],
      body: breakdownRows,
      margin: { left: 15, right: 15 },
      theme: 'grid',
      headStyles: { fillColor: [79, 70, 229] } // Indigo header
    });

    cursorY = doc.lastAutoTable.finalY + 15;
  }

  // 5. Grand Total Summary
  if (estData?.data?.summary) {
    const { total_material_cost, total_labor_cost, grand_total } = estData.data.summary;
    
    // Check page break
    if (cursorY > 250) {
      doc.addPage();
      cursorY = 20;
    }

    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    
    const summaryX = pageWidth - 80;
    doc.text(`Total Materials:`, summaryX, cursorY);
    doc.text(`₹${total_material_cost.toFixed(0)}`, pageWidth - 15, cursorY, { align: "right" });
    cursorY += 7;

    doc.text(`Total Labor:`, summaryX, cursorY);
    doc.text(`₹${total_labor_cost.toFixed(0)}`, pageWidth - 15, cursorY, { align: "right" });
    cursorY += 7;

    doc.line(summaryX, cursorY, pageWidth - 15, cursorY);
    cursorY += 7;

    doc.setFontSize(14);
    doc.text(`Grand Total:`, summaryX, cursorY);
    doc.text(`₹${grand_total.toFixed(0)}`, pageWidth - 15, cursorY, { align: "right" });
  }

  // Footer Disclaimer
  doc.setFontSize(8);
  doc.setFont("helvetica", "italic");
  doc.text("* This is an AI-generated estimate based on image dimensions and standard local rates.", 15, doc.internal.pageSize.getHeight() - 15);
  doc.text("* Actual site conditions may vary. Please consult a professional for an exact quote.", 15, doc.internal.pageSize.getHeight() - 10);

  // Download
  doc.save(`Renovation_Estimate_${session.session_id.substring(0, 8)}.pdf`);
}
