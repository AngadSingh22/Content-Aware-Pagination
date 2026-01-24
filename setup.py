from setuptools import setup, find_packages

setup(
    name="content_aware_pagination",
    version="0.1.0",
    description="A tool for content-aware pagination of long images.",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "opencv-python",
        "numpy",
        "Pillow",
        "reportlab",
        "click",
    ],
    entry_points={
        "console_scripts": [
            "cap=cap.cli:main",
        ],
    },
)
