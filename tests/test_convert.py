# -*- coding: utf-8 -*-
import os
from pytest import approx
import shutil

from py3dtiles import convert_to_ecef
from py3dtiles.convert import convert


def test_convert_to_ecef():
    # results tested with gdaltransform
    [x, y, z] = convert_to_ecef(-75.61200462622627,
                                40.03886513981721,
                                2848.448771114095,
                                4326)
    approx(x, 1215626.30684538)
    approx(y, -4738673.45914053)
    approx(z, 4083122.83975827)


def test_convert():
    # just
    convert(os.path.join(os.path.dirname(os.path.abspath(__file__)), './ripple.las'), outfolder='./tmp')
    assert os.path.exists(os.path.join('tmp', 'tileset.json'))
    assert os.path.exists(os.path.join('tmp', 'r0.pnts'))
    shutil.rmtree('./tmp')



