import setuptools
import sys


def get_version(rel_path):
    with open(rel_path, 'r') as file:
        for line in file.readlines():
            if line.startswith('__version__'):
                delim = '"' if '"' in line else "'"
                return line.split(delim)[1]
        else:
            raise RuntimeError("Unable to find version string.")


if sys.version_info < (3, 8):
    sys.exit('Python < 3.8 not supported.')


setuptools.setup(
    name='ccp',
    version=get_version('ccp/__init__.py'),
    author=['Diego Souza', 'Jones Martins', 'Pedro Paulo Ferreira'],
    packages=setuptools.find_packages(),
    python_requires='>=3.8',
    license='MIT',
    install_requires=[
        'tqdm',  # Python 2.6, 2.7, >= 3.2
        'coloredlogs',
        'psutil',
    ],
    entry_points={
        'console_scripts': [
            'ccp=ccp.client:run',
            'ccpd=ccpd.server:run'
        ]
    },
)