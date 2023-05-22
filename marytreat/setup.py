from setuptools import setup

name = 'MaryTreat'
version = '1.0.1'

setup(
    name=name,
    version=version,
    packages=[''],
    url='',
    license='',
    author='Dia Daur',
    author_email='patiencedaur@gmail.com',
    description='Internal HP Indigo tool to migrate DITA documentation to Tridion Docs',
    install_requires=[
        'requests',
        'zeep',
        'lxml',
        'python-docx'
    ]
)
