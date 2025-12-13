from __future__ import annotations

from pathlib import Path
from setuptools import setup, find_packages

ROOT = Path(__file__).parent
README = (ROOT / "README.md").read_text(encoding="utf-8")

setup(
    name="slack_api",
    version="0.1.0",
    description="Typed contract package for a Slack-like chat service (protocols, models, validators, utils)",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Team 4",
    python_requires=">=3.12,<3.13",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={"slack_api": ["py.typed"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Typing :: Typed",
    ],
)
