# -*- coding: utf-8 -*-

import unittest
import numpy as np
import binascii
# np.set_printoptions(formatter={'int':hex})

from py3dtiles import TileReader, Tile, Feature, B3dm, GlTF

"""
class TestTileReader(unittest.TestCase):

    def test_read(self):
        tile = TileReader().read_file('tests/pointCloudRGB.pnts')

        self.assertEqual(tile.header.version, 1.0)
        self.assertEqual(tile.header.tile_byte_length, 15176)
        self.assertEqual(tile.header.ft_json_byte_length, 148)
        self.assertEqual(tile.header.ft_bin_byte_length, 15000)
        self.assertEqual(tile.header.bt_json_byte_length, 0)
        self.assertEqual(tile.header.bt_bin_byte_length, 0)

        feature_table = tile.body.feature_table
        feature = feature_table.feature(0)
        dcol_res = {'Red': 44, 'Blue': 209, 'Green': 243}
        self.assertDictEqual(dcol_res, feature.colors)
"""

class TestTileBuilder(unittest.TestCase):

    def test_build(self):
        f = open('tests/building.wkb', 'rb')
        wkb = f.read()

        box = [[-8.74748499994166, -7.35523200035095, -2.05385796777344], [8.8036420000717, 7.29930999968201, 2.05386103222656]]
        transform = np.array([
            [1,0,0,1842015.125],
            [0,1,0,5177109.25],
            [0,0,1,247.87364196777344],
            [0,0,0,1]], dtype=float) # translation : 1842015.125, 5177109.25, 247.87364196777344
        transform = transform.flatten('F')
        glTF = GlTF.from_wkb([wkb], [box], transform)
        t = B3dm.from_glTF(glTF)

        # get an array
        tile_arr = t.to_array()
        self.assertEqual(t.header.version, 1.0)
        self.assertEqual(t.header.tile_byte_length, 3036)
        self.assertEqual(t.header.bt_json_byte_length, 0)
        self.assertEqual(t.header.bt_bin_byte_length, 0)
        self.assertEqual(t.header.bt_length, 0)

        t.save_as("/tmp/py3dtiles_test_build_1.b3dm")
