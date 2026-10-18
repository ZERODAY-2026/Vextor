from setuptools import setup, find_packages

setup(
    name="lexiguard",
    version="1.0.0",
    description="Private Legal Document Triage Agent powered by Google Gemma edge models",
    author="Lexiguard Team",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "ollama>=0.3.3",
        "pypdf>=5.0.0",
        "pymupdf>=1.24.11",
        "python-docx>=1.1.2",
        "pydantic>=2.9.2",
        "rich>=13.7.0",
        "psutil>=6.0.0",
        "streamlit>=1.30.0",
        "pytest>=8.3.3",
    ],
    entry_points={
        "console_scripts": [
            "lexiguard = lexiguard.unified:main",
        ],
    },
)
