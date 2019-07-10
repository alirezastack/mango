
from setuptools import setup, find_packages
from mango.core.version import get_version

VERSION = get_version()

f = open('README.md', 'r')
LONG_DESCRIPTION = f.read()
f.close()

setup(
    name='mango',
    version=VERSION,
    description='Survey & Question Management Service',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    author='Sayyed Alireza Hoseini',
    author_email='alireza.hosseini@zoodroom.com',
    url='https://git.zoodroom.com/basket/mango',
    license='unlicensed',
    packages=find_packages(exclude=['ez_setup', 'tests*']),
    package_data={'mango': ['templates/*']},
    include_package_data=True,
    entry_points="""
        [console_scripts]
        mango = mango.main:main
    """,
)
