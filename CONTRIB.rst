Development
==========================

Installing during development
-----------------------------

    During development, you can install the package into a virtual environment
    and continue editing::

        pip install -e ${SRCDIR}

    where SRCDIR is something like $BASEDIR/datatransport/v3/datatransport

    To check PEP8 compliance, use pycodestyle::
        
        https://pypi.org/project/pycodestyle/2.2.0/

        pip install pycodestyle

        pycodestyle --show-source --show-pep8 ${SOURCEFILE}


