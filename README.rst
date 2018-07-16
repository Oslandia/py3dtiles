.. image:: https://secure.travis-ci.org/Oslandia/py3dtiles.png

.. image:: https://badge.fury.io/py/py3dtiles.svg
    :target: https://badge.fury.io/py/py3dtiles

=========
py3dtiles
=========

Python module to manage 3DTiles format.

For now, only the Point Cloud and the Batched 3D Model specifications are supported.

py3dtiles is distributed under LGPL2 or later.


Install
-------

From Docker
~~~~~~~~~~~~

To use py3dtiles in a docker container:

- Build the docker image:

    .. code-block:: shell

        $ git clone https://github.com/Oslandia/py3dtiles
        $ docker built -t py3dtiles .

- Use it:

    .. code-block:: shell

        $ docker run -it --rm -v ${PWD}/data:/data py3dtiles py3dtiles --overwrite True --out /data/output /data/input.las
        $ docker run -it --rm -v ${PWD}/data:/data py3dtiles py3dtiles_info /data/output/r2.pnts


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


If you want to install pythran to fasten computations:

.. code-block:: shell

    (venv)$ pip install pythran
    $ cd py3dtiles
    $ . venv/bin/activate
    (venv)$ py3dtiles/points
    (venv)$ pythran -Ofast -march=native -ffast-math distance_test.py

If you get an error UnicodeDecodeError during pythran install, it's probably a locale issue. Make sure you use a valid locale before install pythran (eg: export LANG=en_US.utf8).

If you wan to run unit tests:

.. code-block:: shell

    (venv)$ pip install nose
    (venv)$ nosetests
    ...

Specifications
--------------

Generic Tile
~~~~~~~~~~~~

The py3dtiles module provides some classes to fit into the
specification:

- *Tile* with a header *TileHeader* and a body *TileBody*
- *TileHeader* represents the metadata of the tile (magic value, version, ...)
- *TileBody* contains varying semantic and geometric data depending on the the tile's type

Moreover, a utility class *TileReader* is available to read a tile
file as well as a simple command line tool to retrieve basic information
about a tile: **py3dtiles\_info**. We also provide a utility to generate a
tileset from a list of 3D models in WKB format or stored in a postGIS table.

**How to use py3dtiles\_info**

Here is an example on how to retrieve basic information about a tile, in this
case *pointCloudRGB.pnts*:

.. code-block:: shell

    $ py3dtiles_info tests/pointCloudRGB.pnts
    Tile Header
    -----------
    Magic Value:  pnts
    Version:  1
    Tile byte length:  15176
    Feature table json byte length:  148
    Feature table bin byte length:  15000

    Feature Table Header
    --------------------
    {'POSITION': {'byteOffset': 0}, 'RGB': {'byteOffset': 12000}, 'POINTS_LENGTH': 1000, 'RTC_CENTER': [1215012.8828876738, -4736313.051199594, 4081605.22126042]}

    First point
    -----------
    {'Z': -0.17107764, 'Red': 44, 'X': 2.19396, 'Y': 4.4896851, 'Green': 243, 'Blue': 209}


**How to use export\_tileset**

Two export modes are available, the database export or the directory export.
They both transform all the geometries provided in .b3dm files, along with a
tileset.json file which organizes them.

The directory export will use all the .wkb files in the provided directory.
Warning: the coordinates are read as floats, not doubles. Make sure to offset
the coordinates beforehand to reduce their size. Afterwards, you can indicate
in the command line the offset that needs to be applied to the tileset so it is
correctly placed. Usage example:

.. code-block:: shell

    $ export_tileset -d my_directory -o 10000 10000 0


The database export requires a user name, a database name, the name of the table
and its column that contains the geometry and (optionaly) the name of the column
that contains the object's ID. Usage example:

.. code-block:: shell

    $ export_tileset -D database -t my_city -c geom -i id -u oslandia


Point Cloud
~~~~~~~~~~~

Points Tile Format:
https://github.com/AnalyticalGraphicsInc/3d-tiles/tree/master/TileFormats/PointCloud

In the current implementation, the *Pnts* class only contains a *FeatureTable*
(*FeatureTableHeader* and a *FeatureTableBody*, which contains features of type
*Feature*).

**How to read a .pnts file**

.. code-block:: python

    >>> from py3dtiles import TileReader
    >>> from py3dtiles import Pnts
    >>>
    >>> filename = 'tests/pointCloudRGB.pnts'
    >>>
    >>> # read the file
    >>> tile = TileReader().read_file(filename)
    >>>
    >>> # tile is an instance of the Tile class
    >>> tile
    <py3dtiles.tile.Tile>
    >>>
    >>> # extract information about the tile header
    >>> th = tile.header
    >>> th
    <py3dtiles.tile.TileHeader>
    >>> th.magic_value
    'pnts'
    >>> th.tile_byte_length
    15176
    >>>
    >>> # extract the feature table
    >>> ft = tile.body.feature_table
    >>> ft
    <py3dtiles.feature_table.FeatureTable
    >>>
    >>> # display feature table header
    >>> ft.header.to_json()
    {'RTC_CENTER': [1215012.8828876738, -4736313.051199594, 4081605.22126042],
    'RGB': {'byteOffset': 12000}, 'POINTS_LENGTH': 1000, 'POSITION': {'byteOffset': 0}}
    >>>
    >>> # extract positions and colors of the first point
    >>> f = ft.feature(0)
    >>> f
    <py3dtiles.feature_table.Feature>
    >>> f.positions
    {'Y': 4.4896851, 'X': 2.19396, 'Z': -0.17107764}
    >>> f.colors
    {'Green': 243, 'Red': 44, 'Blue': 209}

**How to write a .pnts file**

To write a Point Cloud file, you have to build a numpy array with the
corresponding data type.

.. code-block:: python

    >>> from py3dtiles import Feature
    >>> import numpy as np
    >>>
    >>> # create the numpy dtype for positions with 32-bit floating point numbers
    >>> dt = np.dtype([('X', '<f4'), ('Y', '<f4'), ('Z', '<f4')])
    >>>
    >>> # create a position array
    >>> position = np.array([(4.489, 2.19, -0.17)], dtype=dt)
    >>>
    >>> # create a new feature from a uint8 numpy array
    >>> f = Feature.from_array(dt, position.view('uint8'))
    >>> f
    <py3dtiles.feature_table.Feature>
    >>> f.positions
    {'Y': 2.19, 'X': 4.489, 'Z': -0.17}
    >>>
    >>> # create a tile directly from our feature. None is for "no colors".
    >>> t  = Pnts.from_features(dt, None, [f])
    >>>
    >>> # the tile is complete
    >>> t.body.feature_table.header.to_json()
    {'POINTS_LENGTH': 1, 'POSITION': {'byteOffset': 0}}
    >>>
    >>> # to save our tile as a .pnts file
    >>> t.save_as("mypoints.pnts")

<<<<<<< HEAD
**How to convert .las files to 3dtiles**
=======
**How to convert .las files to 3dtiles?**
>>>>>>> fix title formating

The py3dtiles command allows to convert one or several .las files to a single tileset.

.. code-block:: shell

    py3dtiles -h
    usage: py3dtiles [-h] [--out OUT] [--overwrite OVERWRITE] [--jobs JOBS]
                     [--cache_size CACHE_SIZE] [--srs_out SRS_OUT]
                     [--srs_in SRS_IN] [--fraction FRACTION] [--verbose VERBOSE]
                     [--benchmark BENCHMARK]
                     files [files ...]
    Convert .las files to a 3dtiles tileset.
    positional arguments:
      files                 Filenames to process. The file must use the .las
                            format.
    optional arguments:
      -h, --help            show this help message and exit
      --out OUT             The folder where the resulting tileset will be
                            written. (default: ./3dtiles)
      --overwrite OVERWRITE
                            Overwrite the ouput folder if it already exists.
                            (default: False)
      --jobs JOBS           The number of parallel jobs to start. (default: 16)
      --cache_size CACHE_SIZE
                            Cache size in MB (default: 3219)
      --srs_out SRS_OUT     SRS to use as output (EPSG code) (default: None)
      --srs_in SRS_IN       Override input SRS (EPSG code) (default: None)
      --fraction FRACTION   Percentage of the pointcloud to process. (default:
                            100)
      --verbose VERBOSE     Print logs (-1: no logs at all, 0: progress indicator,
                            1 and 2: increased verbosity) (default: 0)
      --benchmark BENCHMARK
                            Print summary at the end of the process (default:
                            None)


Batched 3D Model
~~~~~~~~~~~~~~~~

Batched 3D Model Tile Format:
https://github.com/AnalyticalGraphicsInc/3d-tiles/tree/master/TileFormats/Batched3DModel

**How to read a .b3dm file**

.. code-block:: python

    >>> from py3dtiles import TileReader
    >>> from py3dtiles import B3dm
    >>>
    >>> filename = 'tests/dragon_low.b3dm'
    >>>
    >>> # read the file
    >>> tile = TileReader().read_file(filename)
    >>>
    >>> # tile is an instance of the Tile class
    >>> tile
    <py3dtiles.tile.Tile>
    >>>
    >>> # extract information about the tile header
    >>> th = tile.header
    >>> th
    <py3dtiles.b3dm.B3dmHeader>
    >>> th.magic_value
    'b3dm'
    >>> th.tile_byte_length
    47246
    >>>
    >>> # extract the glTF
    >>> gltf = tile.body.glTF
    >>> gltf
    <py3dtiles.gltf.GlTF>
    >>>
    >>> # display gltf header's asset field
    >>> gltf.header['asset']
    {'premultipliedAlpha': True, 'profile': {'version': '1.0', 'api': 'WebGL'}, 'version': '1.0', 'generator': 'OBJ2GLTF'}

**How to write a .b3dm file**

To write a Batched 3D Model file, you have to import the geometry from a wkb
file containing polyhedralsurfaces or multipolygons.

.. code-block:: python

    >>> import numpy as np
    >>> from py3dtiles import GlTF, TriangleSoup
    >>>
    >>> # load a wkb file
    >>> wkb = open('tests/building.wkb', 'rb').read()
    >>>
    >>> # define the geometry's bouding box
    >>> box = [[-8.75, -7.36, -2.05], [8.80, 7.30, 2.05]]
    >>>
    >>> # define the geometry's world transformation
    >>> transform = np.array([
    ...             [1, 0, 0, 1842015.125],
    ...             [0, 1, 0, 5177109.25],
    ...             [0, 0, 1, 247.87364196777344],
    ...             [0, 0, 0, 1]], dtype=float)
    >>> transform = transform.flatten('F')
    >>>
    >>> # use the TriangleSoup helper class to transform the wkb into arrays
    >>> # of points and normals
    >>> ts = TriangleSoup.from_wkb_multipolygon(wkb)
    >>> positions = ts.getPositionArray()
    >>> normals = ts.getNormalArray()
    >>> # generate the glTF part from the binary arrays.
    >>> # notice that from_binary_arrays accepts array of geometries
    >>> # for batching purposes.
    >>> geometry = { 'position': positions, 'normal': normals, 'bbox': box }
    >>> gltf = GlTF.from_binary_arrays([geometry], transform)
    >>>
    >>> # create a b3dm tile directly from the glTF.
    >>> t = B3dm.from_glTF(glTF)
    >>>
    >>> # to save our tile as a .b3dm file
    >>> t.save_as("mymodel.b3dm")

Third party assets
------------------

Dragon model from Analytical Graphics Inc.'s `3d-tiles samples`_

.. _3d-tiles samples: https://github.com/AnalyticalGraphicsInc/3d-tiles-samples

`Earcut-python`_ by Joshua Skelton

.. _Earcut-python: https://github.com/joshuaskelly/earcut-python

ISC License

Copyright (c) 2016, Mapbox

Permission to use, copy, modify, and/or distribute this software for any purpose
with or without fee is hereby granted, provided that the above copyright notice
and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF
THIS SOFTWARE.
