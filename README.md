# D0C-B0T
This program presents a series of questions to the patient, covering symptoms associated with depression, GAD, panic disorder, and SAD.


Run the program: 

In the terminal, type the following commands to run the Python program:

To install a Python package from a GitHub repository, you can use the git command along with pip. Here are the general steps:

    Make sure you have Git and Python installed on your Linux system.

    Open a terminal.

    Use the following command to clone the repository:

    bash

git clone https://github.com/moderatedan/D0C-B0T.git

Change into the directory where the repository was cloned:

bash

cd D0C-B0T

Now you can install the package using pip. It's recommended to use the -e flag to install it in editable mode, which means changes you make to the code will immediately affect the installed package:

bash

pip install -e .

Alternatively, you can use:

bash

    python setup.py develop

    This will install the package in development mode.

After these steps, you should have the package installed, and you can use it as needed. Keep in mind that the success of these steps depends on the specific project and its dependencies.

Note: Make sure you are using a virtual environment to avoid potential conflicts with your system's Python installation. If you don't have pip installed, you may need to install it using your package manager. For example, on Debian-based systems, you can use:

bash

sudo apt-get install python3-pip


Finally type:

python3 mental_disorder_assessment.py
