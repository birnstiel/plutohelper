import setuptools
from setuptools import setup
import sys
import pathlib

package_name = "plutohelper"
here = pathlib.Path(__file__).absolute().parent


def read_version():
    with (here / package_name / '__init__.py').open() as fid:
        for line in fid:
            if line.startswith('__version__'):
                delim = '"' if '"' in line else "'"
                return line.split(delim)[1]
        else:
            raise RuntimeError("Unable to find version string.")


setup(
    name=package_name,

    description="helper functions for reading pluto output",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="numerical,simulation,science,physics,astrophysics,astronomy",

    #url="https://www.github.com/birnstiel/plutohelper",
    project_urls={"Source Code": "https://www.github.com/birnstiel/plutohelper",
                  "Documentation": "https://www.github.com/birnstiel/plutohelper"
                  },

    author="Til Birnstiel",
    author_email="til.birnstiel@lmu.de",
    maintainer="Til Birnstiel",
    version=read_version(),
    license="MIT",
    packages=setuptools.find_packages(),
    install_requires=["numpy"],
    include_package_data=True,
    zip_safe=False,
)