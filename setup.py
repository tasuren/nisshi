# PySSG - setup

from setuptools import setup
from os.path import exists


NAME = "pyssg"
DESCRIPTION = "Little, simple and fast Static Site Generator."


if exists("README.md"):
    with open("README.md", "r") as f:
        long_description = f.read()
else:
    long_description = DESCRIPTION


with open(f"{NAME}/__init__.py", "r") as f:
    text = f.read()
    version = text.split('__version__ = "')[1].split('"')[0]
    author = text.split('__author__ = "')[1].split('"')[0]


setup(
    name=NAME,
    version=version,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    project_urls={
        "Documentation": f"https://{NAME}.readthedocs.io/",
        "Donate": "https://www.buymeacoffee.com/tasuren",
        "Source Code": f"https://github.com/tasuren/{NAME}",
        "Chat": "https://discord.gg/kfMwZUyGFG"
    },
    author=author,
    author_email='tasuren@aol.com',
    license='MIT',
    keywords='ssg',
    packages=[NAME],
    package_data={NAME: ("py.typed",)},
    entry_points={
        "console_scripts": [
            "pyssg = pyssg.__main__:main"
        ]
    },
    install_requires=[],
    extras_requires={},
    python_requires='>=3.10.0',
    classifiers=[
        'Programming Language :: Python :: 3.10',
        "Topic :: Text Processing :: Markup :: HTML",
        "Environment :: Console",
        'Typing :: Typed'
    ]
)