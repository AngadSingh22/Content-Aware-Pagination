# Content-Aware Pagination ✂️✨

**Because slicing a PDF mid-sentence is a crime against humanity.**

Hi there! Welcome to the tool that saves your long, scroll-happy screenshots from awkward decapitations. We take your massive 10,000-pixel-tall image and gently slice it into neat A4 pages, carefully dodging your handwriting, charts, and diagrams like a ninja avoiding floor creaks.

It’s completely **content-aware**, which is a fancy way of saying "it looks for the blank spots so it doesn't cut your words in half." You're welcome.

## 🌟 Try It Out (Magic in the Browser)

We built a shiny web interface because we love you. It runs **100% in your browser** using PyScript (yes, that means Python running in HTML, what a time to be alive).

👉 **[Launch the Web App](https://your-username.github.io/Content-Aware-Pagination/)**

- **Privacy friendly**: Your images never leave your computer. It’s just you and your browser doing the math.
- **Customizable**: Want A4? A3? A weird custom size because you print on receipts? We got you.
- **Zero Install**: Just click and drag.

## 💻 For the Terminal Hackers

Prefer green text on a black background? I respect that. You can run this locally too.

### Installation

First, feed your Python environment some snacks:

```bash
pip install -e .
```

### Usage

Give it an image, pick a format, and watch it go brrr.

```bash
# The basic "I want A4" approach
python -m cap.cli long_scroll.png --format A4

# The "I am an artist" approach (Custom sizes)
python -m cap.cli long_scroll.png --cut-mode fixed_height_snap --format A3

# The "I refuse to use standard measures" approach
# (Note: Web UI is easier for custom sizes, just saying)
```

## 🧠 How it Works

1.  **Ink Density Analysis**: We scan your image line-by-line to see where the "ink" (pixels) are.
2.  **Safe Zone Detection**: We find the quiet valleys of whitespace between your loud mountains of text.
3.  **Optimal Cutting**: We use Dynamic Programming to find the mathematically perfect cut points that minimize awkward gaps while keeping pages roughly the same size.
4.  **Profit**: You get a PDF that doesn't look like a toddler attacked it with scissors.

## 🤝 Contributing

Found a bug? Want to add support for circular paper? PRs are welcome! Just remember: **No comments in the code.** We like our codebase like we like our coffee—black, strong, and completely silent.

---
*Made with 💜, Python, and too much caffeine.*
