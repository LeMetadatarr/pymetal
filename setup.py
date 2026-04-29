from setuptools import find_packages, setup

setup(
    name="pymetal",
    version="0.6.0",
    packages=find_packages(exclude=("test", "test.*", "examples")),
    install_requires=[
        "curl_cffi",
        "lxml",
        "pydantic>=2",
        "random-user-agent",
    ],
    url="https://www.github.com/OpenJarbas/pymetal",
    license="Apache2.0",
    author="jarbasAi",
    author_email="jarbasai@mailfence.com",
    description="metal-archives.com Python client with a relational data model",
)
