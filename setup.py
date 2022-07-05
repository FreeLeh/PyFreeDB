from setuptools import find_packages, setup

requirements = []
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="pyfreeleh",
    version="0.1.0",
    install_requires=requirements,
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.6",
)
