from setuptools import find_packages, setup

setup(
    name="pyfreedb",
    version="0.1.0",
    packages=find_packages(include=["exampleproject", "exampleproject.*"]),
)
