# Content-Aware Pagination 

Hello. This is largely nothing crazy. It takes your long-scroll image and gently slices it into neat A4 pages, carefully dodging your handwriting, charts, and diagrams. I am not exactly sure why I have 10,000 pixels tall images, maybe its just me but hoping this 6 hours of work will save me a lot of time in the future.

It’s completely content-aware, which is a fancy way of saying "it looks for the blank spots so it doesn't cut your words in half." You're welcome. Your images never leave your computer. It’s just you and your browser doing the math because my handwriting is bad enough for it to be not in public for my social sanity.


## Try It Out (Please)
 [Launch the Web App](https://angadsingh22.github.io/Content-Aware-Pagination/)

Prefer green text(or blue) on a black background? I respect that. You can run this locally too.

### Installation

Your Python environment

```bash
pip install -e .
```

### Usage

Give it an image, pick a format, and watch it go brrr.

```bash
# The basic  approach
python -m cap.cli long_scroll.png --format A4

# The custom sizes approach
python -m cap.cli long_scroll.png --cut-mode fixed_height_snap --format A3


##  How it Works

It scans your image line-by-line to see where the "ink" (pixels) are. It finds the whitespace between your mountains of text.
then It uses Dynamic Programming to find the mathematically perfect cut points that minimize awkward gaps while keeping pages roughly the same size.You get a PDF (or images), whichever one is most convinient to you.



---
