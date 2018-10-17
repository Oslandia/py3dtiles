Install
-------

From sources
~~~~~~~~~~~~

To use py3dtiles from sources:

.. code-block:: shell

    $ apt install git python3 python3-pip virtualenv libopenblas-base liblas-c3
    $ git clone https://github.com/Oslandia/py3dtiles
    $ cd py3dtiles
    $ virtualenv -p /usr/bin/python3 venv
    $ . venv/bin/activate
    (venv)$ pip install -e .
    (venv)$ python setup.py install

If you want to run unit tests:

.. code-block:: shell

    (venv)$ pip install pytest pytest-benchmark
    (venv)$ pytest
    ...

With docker
~~~~~~~~~~~~

Build the py3dtiles docker image:

.. code-block:: shell

    $ git clone https://github.com/Oslandia/py3dtiles
    $ cd py3dtiles
    $ docker build -t py3dtiles .

Then, you can use the py3dtiles docker image :

.. code-block:: shell

    $ docker run -it --rm py3dtiles
    $ docker run -it --rm py3dtiles py3dtiles --help
    $ docker run -it --rm py3dtiles py3dtiles info ... 

Learn how to use the `command line interface <https://github.com/Oslandia/py3dtiles/blob/master/docs/cli.rst>`_.
