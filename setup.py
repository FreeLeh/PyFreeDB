from setuptools import find_packages, setup

install_requires = [
    "google-api-python-client==2.51.0",
    "google-auth-httplib2==0.1.0",
    "google-auth-oauthlib==0.5.2",
    "requests==2.28.1",
]

setup(
    name="pyfreedb",
    version="0.0.1",
    install_requires=install_requires,
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.7",
)
