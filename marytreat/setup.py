from setuptools import setup

name = 'MaryTreat'
version = '0.1.0'

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

"""
Sure, here are some simple instructions for installing a .whl package:

1. Download the .whl package file to your computer. 
2. Open a command prompt on your computer. 
   * For Windows, you can do this by pressing the "Windows Key + R" to open the Run dialog box, typing "cmd", and then pressing Enter.
3. Navigate to the directory where you saved the .whl package by typing `cd <path_to_directory>` and pressing Enter.
4. Type `pip install <whl_filename>` and press Enter. This will install the package.
5. During the installation process, you may be prompted to enter your name and password. Make sure to enter them correctly.
6. After installation, you should be able to run the program. The logs directory should be exposed in the project root.

That's it!

While it is possible to create a Tkinter form in setup.py to ask for user input, it is not recommended. The `setup.py` script is not meant to have a graphical user interface as it runs in a console environment. It is better to ask for user input during runtime of the application instead of setup.

However, here is an example of how to use a `setup.py` script to create a file named `secrets.py` with the user's input:

```python
from setuptools import setup
from os.path import exists

def main():
    # Get user input
    username = input("Enter username: ")
    password = input("Enter password: ")
    
    # Create secrets.py file
    with open('secrets.py', 'w') as f:
        f.write(f'username = "{username}"\n')
        f.write(f'password = "{password}"\n')
    
    # Run setup
    setup(
        name='my_package',
        version='1.0.0',
        packages=['my_package'],
    )

if __name__ == '__main__':
    main()
```

Note that this is just an example and should not be used in production code.
It is recommended to ask for user input during runtime of the application and not during installation/setup.
"""