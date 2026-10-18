from setuptools import setup, find_packages

setup(
    name="lexiguard",
    version="1.0.0",
    description="Private Legal Document Triage Agent powered by Google Gemma edge models",
    author="Lexiguard Team",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "ollama>=0.4.0",
        "pypdf>=5.0.0",
        "pydantic>=2.7.0",
        "rich>=13.7.0",
        "psutil>=5.9.0",
        "streamlit>=1.30.0",
    ],
    entry_points={
        "console_scripts": [
            "lexiguard = lexiguard.unified:main",
        ],
    },
)
