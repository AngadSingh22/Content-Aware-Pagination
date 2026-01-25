from PIL import Image
from reportlab.pdfgen import canvas
import os
import cv2
import numpy as np
from enum import Enum

class RenderMode(Enum):

    VARIABLE_SIZE = "variable_size"
    FIXED_SIZE_WITH_PADDING = "fixed_size_with_padding"

def load_image(path):

    pil_img = Image.open(path)

    if pil_img.mode not in ('RGB', 'L'):
        pil_img = pil_img.convert('RGB')
    return np.array(pil_img)

def save_pdf_from_crops(crop_images, output_path, dpi=300, render_mode=RenderMode.VARIABLE_SIZE,
                        target_height_px=None, padding_color=(255, 255, 255)):

    if not crop_images:
        return

    c = canvas.Canvas(output_path)

    for img in crop_images:
        if isinstance(img, np.ndarray):
            img = Image.fromarray(img)


        if render_mode == RenderMode.FIXED_SIZE_WITH_PADDING and target_height_px is not None:
            img = _pad_to_target_height(img, target_height_px, padding_color)

        width_px, height_px = img.size

        width_pt = width_px * 72 / dpi
        height_pt = height_px * 72 / dpi

        c.setPageSize((width_pt, height_pt))


        temp_name = f"temp_page_{os.getpid()}_{id(img)}.png"
        img.save(temp_name)

        c.drawImage(temp_name, 0, 0, width=width_pt, height=height_pt)
        c.showPage()

        try:
            os.remove(temp_name)
        except OSError:
            pass

    c.save()

def _pad_to_target_height(img, target_height_px, padding_color=(255, 255, 255)):

    width, height = img.size

    if height >= target_height_px:

        return img


    padded = Image.new(img.mode, (width, target_height_px), padding_color)


    padded.paste(img, (0, 0))

    return padded
