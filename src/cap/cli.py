import click
import os
import sys
from .core import compute_ink_density, find_optimal_cuts_dp
from .io import load_image, save_pdf_from_crops
from PIL import Image
import numpy as np

# Standard sizes in mm
PAPER_SIZES = {
    "A4": (210, 297),
    "A3": (297, 420),
    "B5": (176, 250),
}

@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output PDF path. Defaults to input_paginated.pdf")
@click.option("--format", "-f", default="A4", type=click.Choice(list(PAPER_SIZES.keys()) + ["CUSTOM"]), help="Page format (A4, A3, B5)")
@click.option("--dpi", "-d", default=300, help="DPI for physical size calculation")
@click.option("--window-frac", default=0.04, help="Search window fraction of page height")
@click.option("--min-gap", default=12, help="Minimum gap rows to consider safe")
def main(input_path, output, format, dpi, window_frac, min_gap):
    """
    Content-Aware Pagination Tool.
    
    Splits a long image into pages avoiding text cuts.
    """
    if output is None:
        base, _ = os.path.splitext(input_path)
        output = f"{base}_paginated.pdf"
        
    click.echo(f"Processing {input_path}...")
    
    # 1. Load Image
    try:
        # Load as numpy for processing, but keep reference for cropping if needed?
        # Our io.load_image returns numpy array.
        # But we need PIL image for cropping efficiently or just slice the numpy array.
        # Let's check io.py: load_image returns np.array.
        # To crop, we can slice numpy array.
        img_array = load_image(input_path)
    except Exception as e:
        click.echo(f"Error loading image: {e}", err=True)
        sys.exit(1)
        
    height, width, _ = img_array.shape if len(img_array.shape) == 3 else (img_array.shape[0], img_array.shape[1], 1)
    
    # 2. Determine Target Height
    if format in PAPER_SIZES:
        w_mm, h_mm = PAPER_SIZES[format]
        # We need to map width of image to physical width or just use height ratio?
        # Usually, we want the image width to fit on the page width.
        # scaling_factor = image_width_px / (page_width_mm * dpi / 25.4)
        # But here we want to slice the image to fit onto pages.
        # If we print at 1:1, the pixel height of the page is:
        # h_px = h_mm / 25.4 * dpi
        target_height_px = int(h_mm / 25.4 * dpi)
        
        # Adjust if image resolution implies different size?
        # The user says "same high fidelity", so 1:1 mapping.
        # We just cut chunks of target_height_px.
    else:
        # Custom... just assume A4 for now or ask user for height
        target_height_px = int(297 / 25.4 * dpi)
        
    click.echo(f"Image Size: {width}x{height}")
    click.echo(f"Target Page Height: {target_height_px} px (@ {dpi} DPI)")

    # 3. Compute Ink Density
    click.echo("Analyzing ink density...")
    ink_profile = compute_ink_density(img_array)
    
    # 4. Find Cuts (DP)
    click.echo("Finding optimal cuts (DP)...")
    cuts = find_optimal_cuts_dp(ink_profile, target_height_px, 
                                window_frac=window_frac, 
                                min_gap_rows=min_gap)
                                
    click.echo(f"Found {len(cuts)-1} pages.")
    
    # 5. Crop and Save
    files_to_save = []
    
    # load PIL image for clean cropping (or reuse numpy)
    # Re-opening as PIL to preserve metadata/quality if we were careful, 
    # but numpy conversion is already lossy if we aren't careful.
    # Actually io.load_image returned numpy. Let's just use numpy slices.
    
    for i in range(len(cuts) - 1):
        start = cuts[i]
        end = cuts[i+1]
        
        # Simple slice
        page_crop = img_array[start:end, :]
        files_to_save.append(page_crop)
        
    click.echo(f"Saving to {output}...")
    save_pdf_from_crops(files_to_save, output, dpi=dpi)
    click.echo("Done!")

if __name__ == "__main__":
    main()
