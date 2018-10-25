# -*- coding: utf-8 -*-
import json
import unittest
from py3dtiles import BoundingVolume, HelperTest, TileForReal, TileSet


class Test_TileSet(unittest.TestCase):

    def test_basics(self):
        helper = HelperTest()
        helper.sample_file_names.append('TileSet_CanaryWharf.json')
        helper.test_load_reference_files()
        validator = lambda x: TileSet().validate(x)
        if not helper.test_validate_reference_files(validator):
            self.fail()

    def build_sample(self):
        """
        Programmatically define a tileset sample encountered in the
        TileSet json header specification cf
        https://github.com/AnalyticalGraphicsInc/3d-tiles/tree/master/specification#tileset-json
        :return: the sample as TileSet object.
        """
        tile_set = TileSet()
        bv = BoundingVolume()
        bv.set("box", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        root_tile = TileForReal()
        root_tile.set_bounding_volume(bv)
        root_tile.set_geometric_error(3.14159)
        tile_set.set_root_tile(root_tile)
        #FIXME bt.add_property_from_array("id",
        #FIXME                           ["unique id", "another unique id"])
        return tile_set

    def test_json_encoding(self):
        return self.build_sample().to_json()

    def test_tileset_build_sample_and_validate(self):
        tile_set_from_json = json.loads(self.test_json_encoding())
        if not TileSet().validate(tile_set_from_json):
            print('tile_set_from_json is not valid against the schema')
            self.fail()

if __name__ == "__main__":
    unittest.main()
