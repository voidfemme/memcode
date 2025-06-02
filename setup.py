"""
Setup configuration for MemCode.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="memcode",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="AI-powered function generation with intelligent memory and context retrieval",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/memcode",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "black>=23.11.0",
            "isort>=5.12.0",
            "mypy>=1.7.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "memcode=app.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "memcode": ["*.toml", "*.yml", "*.yaml"],
    },
)
