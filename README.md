# Content Aware Pagination

A tool for "content-aware pagination" of long images (e.g., scrolled screenshots, scanned notes). It slices high-resolution images into standard page sizes (A4, A3, B5) without cutting through handwriting or text.

## Features

- **Ink Density Analysis**: Detects gaps between lines of text to find safe cutting points.
- **High Fidelity**: Preserves original image quality with 1:1 pixel mapping (no resampling unless necessary).
- **Flexible Output**: Supports standard paper sizes (A4, A3, B5) and custom formats.
- **Robust Fallbacks**: Handles dense pages with overlap or minimal scaling options.

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

## Usage

### CLI

```bash
python -m cap.cli input_long_image.png --format A4 --dpi 300 --output paginated.pdf
```

### Python API

```python
from cap import paginate_image

paginate_image("input.png", output="output.pdf", page_format="A4")
```

## Website

Check out the [documentation](https://ahuja.github.io/Content_Aware_Pagination) (placeholder link).
