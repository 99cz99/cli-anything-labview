"""Setup for cli-anything-labview — PEP 420 namespace package."""

from pathlib import Path
from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-labview",
    version="1.0.0",
    description="CLI harness for NI LabVIEW — control LabVIEW from the command line",
    long_description=(Path(__file__).parent / "cli_anything/labview/README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author="cli-anything contributors",
    author_email="1978225964@qq.com",
    url="https://github.com/99cz99/cli-anything-labview",
    license="Apache License 2.0",
    python_requires=">=3.10",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    package_data={
        "cli_anything.labview": ["skills/*.md"],
    },
    install_requires=[
        "click>=8.0",
        "pywin32>=300; sys_platform == 'win32'",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov",
        ],
    },
    entry_points={
        "console_scripts": [
            "cli-anything-labview=cli_anything.labview.labview_cli:cli",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Testing",
    ],
    keywords="labview, cli, automation, activex, com, vi, test, measurement",
)
