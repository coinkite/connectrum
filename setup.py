""" Setup file """
import os
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(HERE, 'README.md')).read()


def get_version():
    with open("connectrum/__init__.py") as f:
        for line in f:
            if line.startswith("__version__"):
                return eval(line.split("=")[-1])

REQUIREMENTS = [
    'aiosocks',
    'bottom>=1.0.2'
]

TEST_REQUIREMENTS = [
    'aiohttp',
    'pytest',
    'tox',
]

if __name__ == "__main__":
    setup(
        name='connectrum',
        version=get_version(),
        description="asyncio-based Electrum client library",
        long_description=README,
        classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Topic :: Software Development :: Libraries',
        ],
        author='Peter Gray',
        author_email='peter@coinkite.com',
        url='https://github.com/coinkite/connectrum',
        license='MIT',
        keywords='electrum bitcoin asnycio client',
        platforms='any',
        include_package_data=True,
        packages=find_packages(exclude=('testing', 'examples')),
        #data_files=['connectrum/servers.json'],
        install_requires=REQUIREMENTS,
        tests_require=REQUIREMENTS + TEST_REQUIREMENTS,
    )
