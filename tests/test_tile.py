# -*- coding: utf-8 -*-
import json
import unittest
from py3dtiles import BoundingVolume, ExtensionSet, HelperTest, TileForReal


class Test_Tile(unittest.TestCase):

    def setUp(self):
        self.schemas = ExtensionSet()
        file_name = 'py3dtiles/jsonschemas/tile.schema.json'
        try:
            self.schemas.append_schema_from_file(file_name)
        except:
            print(f'Unable to define extension {file_name}')
            self.fail()

    def tearDown(self):
        self.schemas.delete_schemas()

    def test_basics(self):
        helper = HelperTest()
        helper.sample_file_names.append(
                              'Tile_box_bounding_volume_sample.json')
        helper.test_load_reference_files()

    def test_json_reference_sample(self):
        json_reference = HelperTest.load_json_reference_file(
                                    'Tile_box_bounding_volume_sample.json')
        if not self.schemas.validate("Tile", json_reference):
            print('Invalid item')
            self.fail()

    def build_sample(self):
        """
        Programmatically define a tile (which illustrates the API).
        """
        bv = BoundingVolume()
        bv.add_property_from_array('box',
                                   [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        tile = TileForReal()
        tile.set_bounding_volume(bv)
        tile.set_geometric_error(3.14159)
        return tile

    def test_json_encoding(self):
        self.build_sample().to_json()

    def test_build_sample_and_validate(self):
        """
        Assert the build sample is valid against the schema
        """
        string_json_tile = self.build_sample().to_json()
        tile = json.loads(string_json_tile)

        if not self.schemas.validate("Tile", tile):
            print('Build tile is not valid against the schema.')
            self.fail()

if __name__ == "__main__":
    unittest.main()
