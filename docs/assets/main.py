import asyncio
from pyscript import window, document
import io
import cv2
import numpy as np
import base64
from PIL import Image

try:
    from core import compute_ink_density, find_optimal_cuts_dp, CutMode
except ImportError:
    pass

PAPER_SIZES = {
    "A4": (210, 297),
    "A3": (297, 420),
    "B5": (176, 250),
}

def get_target_height_px(format_name, dpi, custom_w_mm=None, custom_h_mm=None):
    if format_name == "CUSTOM" and custom_h_mm is not None:
        h_mm = float(custom_h_mm)
    elif format_name in PAPER_SIZES:
        _, h_mm = PAPER_SIZES[format_name]
    else:
        _, h_mm = PAPER_SIZES["A4"]
    
    return int(h_mm / 25.4 * dpi)

def process_image(event):
    try:
        
        uploaded_bytes = window.uploadedFileBytes
        if not uploaded_bytes:
            window.alert("No file uploaded!")
            return

        array = np.asarray(uploaded_bytes.to_py())
        img_array = cv2.imdecode(array, cv2.IMREAD_COLOR)

        if img_array is None:
            raise ValueError("Could not decode image")
        
        format_val = document.getElementById("format-select").value
        cut_mode_val = document.getElementById("cut-mode-select").value
        dpi_val = int(document.getElementById("dpi-input").value)
        
        custom_w = None
        custom_h = None
        if format_val == "CUSTOM":
            custom_w = document.getElementById("custom-width").value
            custom_h = document.getElementById("custom-height").value

        target_height = get_target_height_px(format_val, dpi_val, custom_w, custom_h)
        
        ink_profile = compute_ink_density(img_array)
        
        mode_enum = CutMode.WHITESPACE if cut_mode_val == "whitespace" else CutMode.FIXED_HEIGHT_SNAP
        
        cuts = find_optimal_cuts_dp(ink_profile, target_height, cut_mode=mode_enum, snap_px=40)
        
        crops = []
        for i in range(len(cuts) - 1):
            start = cuts[i]
            end = cuts[i+1]
            crop_cv2 = img_array[start:end, :]
            
            crop_rgb = cv2.cvtColor(crop_cv2, cv2.COLOR_BGR2RGB)
            crop_pil = Image.fromarray(crop_rgb)
            crops.append(crop_pil)

        if crops:
            pdf_bytes = io.BytesIO()
            crops[0].save(
                pdf_bytes, "PDF", resolution=dpi_val, 
                save_all=True, append_images=crops[1:]
            )
            pdf_bytes.seek(0)
            
            pdf_b64 = base64.b64encode(pdf_bytes.read()).decode('ascii')
            data_url = f"data:application/pdf;base64,{pdf_b64}"
            
            orig_name = window.uploadedFile.name
            base_name = orig_name.rsplit('.', 1)[0]
            new_name = f"{base_name}_paginated.pdf"
            
            window.processingComplete(data_url, new_name)
        
    except Exception as e:
        print(f"Error: {e}")
        error_msg_el = document.getElementById("status-text")
        if error_msg_el:
            error_msg_el.innerText = f"Error: {str(e)}"

window.addEventListener('process-trigger', process_image)
