from setuptools import setup, find_packages, Distribution
import os
import glob


def list_file(pth):
    return [os.path.basename(c) for c in glob.glob(rf'{pth}\*')]


with open('requirements.txt') as f:
    required = f.read().splitlines()


class BinaryDistribution(Distribution):
    """Distribution which always forces a binary package with platform name"""
    def has_ext_modules(foo):
        return True

setup(
    name='hardware_station_common_wpf',
    version='1.0.0.0',
    url='',
    license='',
    author='elton',
    author_email='elton.tian@group.com',
    description='',
    classifiers=[  # Optional
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'License :: Other/Proprietary License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),  # Required
    install_requires=required,  # Optional
    package_data={  # Optional
        '': list_file('hardware_station_common'),
    },
    distclass=BinaryDistribution
)
