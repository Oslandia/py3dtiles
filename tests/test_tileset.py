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

    def unmature_test_json_reference_sample(self):
        json_to_test = HelperTest.load_json_reference_file(
                                             self.sample_file_names[0])
        if not TileSet().validate(json_to_test):
            print('Invalid reference file.')
            self.fail()

    def build_tileset_sample(self):
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
        tile_set = self.build_tileset_sample()  # A TileSet instance
        return tile_set.to_json()               # A JSON formatted string

    def test_tileset_build_sample_and_validate(self):
        string_json_tile_set = self.test_json_encoding()
        tile_set_from_json = json.loads(string_json_tile_set)  # A Python object

        if not TileSet().validate(tile_set_from_json):
            print('tile_set_from_json is not valid against the schema')
            self.fail()

if __name__ == "__main__":
    unittest.main()
