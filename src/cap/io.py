from PIL import Image
from reportlab.pdfgen import canvas
import os
import cv2
import numpy as np

def load_image(path):
    """Loads image and converts to numpy array for CV2."""
    pil_img = Image.open(path)
    # Convert to RGB if needed to ensure CV2 compatibility
    if pil_img.mode not in ('RGB', 'L'):
        pil_img = pil_img.convert('RGB')
    return np.array(pil_img)

def save_pdf_from_crops(crop_images, output_path, dpi=300):
    """
    Saves a list of numpy array images/PIL images as PDF.
    
    Args:
        crop_images: List of numpy arrays or PIL Images
        output_path: Destination
        dpi: Print resolution
    """
    if not crop_images:
        return

    c = canvas.Canvas(output_path)
    
    for img in crop_images:
        if isinstance(img, np.ndarray):
            img = Image.fromarray(img)
            
        width_px, height_px = img.size
        # 72 points per inch
        width_pt = width_px * 72 / dpi
        height_pt = height_px * 72 / dpi
        
        c.setPageSize((width_pt, height_pt))
        
        # Save temp for ReportLab
        temp_name = f"temp_page_{os.getpid()}_{id(img)}.png"
        img.save(temp_name)
        
        c.drawImage(temp_name, 0, 0, width=width_pt, height=height_pt)
        c.showPage()
        
        try:
            os.remove(temp_name)
        except OSError:
            pass
            
    c.save()
