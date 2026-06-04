"""
Setup script for lexashield-engine-sdk

For most use cases, use pyproject.toml instead.
This file is provided for backward compatibility.
"""

from setuptools import setup, find_packages

# Read the contents of README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="lexashield-engine-sdk",
    version="2.0.6",
    author="LexaShield Team",
    author_email="prashant@lexashield.com",
    description="SDK for building LexaShield processing engines",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    package_data={
        "lexashield_engine": [
            "pdf_assets/*.pdf",
            "pdf_assets/*.png",
            "pdf_assets/*.css",
        ],
    },
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.136.1",
        "uvicorn[standard]>=0.46.0",
        "pydantic>=2.13.3",
        "pydantic-settings>=2.14.0",
        "aiohttp>=3.13.5",
        "python-multipart>=0.0.27",
        "tenacity>=9.1.4",
        "pyhtml2pdf>=0.1.0",
        "pypdf>=6.10.2",
        "boto3==1.43.2",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "mypy>=1.5.0",
            "ruff>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "lexashield-engine=lexashield_engine.cli:main",
        ],
    },
)
