from setuptools import setup, find_packages

name = 'MaryTreat Indigo'
version = '1.1.0'

setup(
    name=name,
    version=version,
    packages=find_packages(),
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
