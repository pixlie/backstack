from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="backstack",
    version="0.0.2",
    author="Sumit Datta",
    author_email="brainless@pixlie.com",
    description="An opinionated RESTful backend framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pixlie/backstack",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
    install_requires=[
        "sanic",
        "sanic-auth",
        "authomatic",
        "pymemcache",
        "psycopg2-binary",
        "python-decouple",
        "sqlalchemy",
        "sqlalchemy-migrate",
        "marshmallow",
        "passlib",
        "aioamqp",
        "ujson",
        "faker",
        "sanic-ipware"
    ]
)
