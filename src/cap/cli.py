import click
import os
import sys
from .core import compute_ink_density, find_optimal_cuts_dp, CutMode
from .io import load_image, save_pdf_from_crops, RenderMode
from PIL import Image
import numpy as np


PAPER_SIZES = {
    "A4": (210, 297),
    "A3": (297, 420),
    "B5": (176, 250),
}

@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="Output path (PDF or directory for images)")
@click.option("--output-format", default="pdf", type=click.Choice(["pdf", "images"]),
              help="Output format: pdf (single file) or images (multiple PNG files)")
@click.option("--format", "-f", default="A4", type=click.Choice(list(PAPER_SIZES.keys()) + ["CUSTOM"]), help="Page format (A4, A3, B5)")
@click.option("--dpi", "-d", default=300, help="DPI for physical size calculation")
@click.option("--window-frac", default=0.04, help="Search window fraction of page height")
@click.option("--min-gap", default=12, help="Minimum gap rows to consider safe")
@click.option("--cut-mode", default="whitespace", type=click.Choice(["whitespace", "fixed_height_snap"]),
              help="Cut strategy: whitespace (flexible) or fixed_height_snap (deterministic)")
@click.option("--render-mode", default="variable_size", type=click.Choice(["variable_size", "fixed_size_with_padding"]),
              help="Render strategy: variable_size or fixed_size_with_padding")
@click.option("--snap-px", default=40, help="Snap neighborhood radius in pixels for fixed_height_snap mode")
@click.option("--unsafe-window", default=2, help="Window radius for unsafe cut detection")
@click.option("--unsafe-threshold", default=0.3, help="Ink threshold for unsafe cut detection")
def main(input_path, output, output_format, format, dpi, window_frac, min_gap, cut_mode, render_mode, snap_px, unsafe_window, unsafe_threshold):

    if output is None:
        base, _ = os.path.splitext(input_path)
        if output_format == "pdf":
            output = f"{base}_paginated.pdf"
        else:
            output = f"{base}_pages"

    click.echo(f"Processing {input_path}...")


    try:
        img_array = load_image(input_path)
    except Exception as e:
        click.echo(f"Error loading image: {e}", err=True)
        sys.exit(1)

    height, width, _ = img_array.shape if len(img_array.shape) == 3 else (img_array.shape[0], img_array.shape[1], 1)


    if format in PAPER_SIZES:
        w_mm, h_mm = PAPER_SIZES[format]
        target_height_px = int(h_mm / 25.4 * dpi)
    else:

        target_height_px = int(297 / 25.4 * dpi)

    click.echo(f"Image Size: {width}x{height}")
    click.echo(f"Target Page Height: {target_height_px} px (@ {dpi} DPI)")
    click.echo("Analyzing ink density...")
    ink_profile = compute_ink_density(img_array)


    cut_mode_enum = CutMode.WHITESPACE if cut_mode == "whitespace" else CutMode.FIXED_HEIGHT_SNAP
    render_mode_enum = RenderMode.VARIABLE_SIZE if render_mode == "variable_size" else RenderMode.FIXED_SIZE_WITH_PADDING

    click.echo(f"Cut Mode: {cut_mode}, Render Mode: {render_mode}")
    click.echo("Finding optimal cuts (DP)...")
    cuts = find_optimal_cuts_dp(ink_profile, target_height_px,
                                window_frac=window_frac,
                                min_gap_rows=min_gap,
                                cut_mode=cut_mode_enum,
                                snap_px=snap_px,
                                unsafe_window_radius=unsafe_window,
                                unsafe_ink_threshold=unsafe_threshold)

    click.echo(f"Found {len(cuts)-1} pages.")


    crops = []

    for i in range(len(cuts) - 1):
        start = cuts[i]
        end = cuts[i+1]
        page_crop = img_array[start:end, :]
        crops.append(page_crop)


    if output_format == "pdf":
        click.echo(f"Saving to {output}...")
        save_pdf_from_crops(crops, output, dpi=dpi,
                            render_mode=render_mode_enum,
                            target_height_px=target_height_px)
        click.echo("Done!")
    else:

        os.makedirs(output, exist_ok=True)
        click.echo(f"Saving {len(crops)} images to {output}/...")

        for i, crop in enumerate(crops):

            if isinstance(crop, np.ndarray):
                crop_img = Image.fromarray(crop)
            else:
                crop_img = crop


            if render_mode_enum == RenderMode.FIXED_SIZE_WITH_PADDING and target_height_px is not None:
                from .io import _pad_to_target_height
                crop_img = _pad_to_target_height(crop_img, target_height_px)


            output_path = os.path.join(output, f"page_{i+1:03d}.png")
            crop_img.save(output_path, "PNG")

        click.echo(f"Done! Saved {len(crops)} images to {output}/")

if __name__ == "__main__":
    main()
