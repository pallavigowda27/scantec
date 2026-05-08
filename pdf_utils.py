import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import tempfile

def generate_pdf_report(original_img, heatmap_img, prediction, confidence_str, notes, patient_name="", patient_age=""):
    """
    Generate a PDF report containing the original X-ray, Heatmap, analysis, and patient info.
    Returns the path to the generated PDF.
    """
    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, 750, "ScanTec - Medical Diagnostic Report")
    
    c.setFont("Helvetica", 14)
    c.drawString(50, 715, f"Patient Name: {patient_name if patient_name else 'N/A'}")
    c.drawString(350, 715, f"Age: {patient_age if patient_age else 'N/A'}")
    c.line(50, 705, 550, 705)
    
    c.drawString(50, 680, f"Prediction: {prediction}")
    c.drawString(50, 660, f"Confidence: {confidence_str}%")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 620, "Original X-Ray")
    c.drawString(320, 620, "Grad-CAM Heatmap (ROL)")
    
    # Save PIL images to temp files to read them into reportlab
    fd1, temp_orig = tempfile.mkstemp(suffix=".png")
    os.close(fd1)
    original_img.save(temp_orig)
    
    fd2, temp_heat = tempfile.mkstemp(suffix=".png")
    os.close(fd2)
    heatmap_img.save(temp_heat)
    
    # Draw images
    c.drawImage(ImageReader(temp_orig), 50, 380, width=250, height=250, preserveAspectRatio=True)
    c.drawImage(ImageReader(temp_heat), 320, 380, width=250, height=250, preserveAspectRatio=True)
    
    # Doctor Notes
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 340, "Doctor's Notes:")
    c.setFont("Helvetica", 12)
    
    # Wrap text
    from textwrap import wrap
    lines = wrap(notes, width=80)
    y_pos = 320
    for line in lines:
        c.drawString(50, y_pos, line)
        y_pos -= 15
        
    c.save()
    
    # Clean up temp images
    try:
        os.remove(temp_orig)
        os.remove(temp_heat)
    except:
        pass
        
    return pdf_path

def generate_simple_pdf_report(prediction, confidence, notes, patient_name="", patient_age=""):
    """
    Generate a simple text-based PDF report.
    """
    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, 750, "ScanTec - Medical Diagnostic Report")
    
    c.setFont("Helvetica", 14)
    c.drawString(50, 715, f"Patient Name: {patient_name if patient_name else 'N/A'}")
    c.drawString(350, 715, f"Age: {patient_age if patient_age else 'N/A'}")
    c.line(50, 705, 550, 705)
    
    c.drawString(50, 680, f"Prediction: {prediction}")
    c.drawString(50, 660, f"Confidence: {confidence:.2f}%")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 620, "Doctor's Notes:")
    c.setFont("Helvetica", 12)
    
    from textwrap import wrap
    lines = wrap(notes, width=80)
    y_pos = 600
    for line in lines:
        c.drawString(50, y_pos, line)
        y_pos -= 15
        
    c.save()
    return pdf_path
