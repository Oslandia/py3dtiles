# -*- coding: utf-8 -*-

import json
import unittest
from py3dtiles import BoundingVolume, ExtensionSet, TileForReal, TileSet


class Test_TileSet(unittest.TestCase):

    def setUp(self):
        self.schemas = ExtensionSet()
        file_name = 'py3dtiles/jsonschemas/tileset.schema.json'
        try:
            self.schemas.append_schema_from_file(file_name)
        except:
            print(f'Unable to define extension {file_name}')
            self.fail()

    def tearDown(self):
        self.schemas.delete_schemas()

    def test_load_reference_file(self):
        try:
            reference_file = 'tests/data/CanaryWharf_tileset.json'
            json_reference = json.loads(open(reference_file, 'r').read())
            json_reference.pop('_comment', None)  # Drop the "comment".
        except:
            print(f'Unable to parse reference file {reference_file}')
            self.fail()
        return json_reference

    def test_json_reference_sample(self):
        json_reference = self.test_load_reference_file()
        if not self.schemas.validate("Tileset", json_reference):
            print('Invalid item')
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

    def unmature_test_tileset_build_sample_and_validate(self):
        """
        Assert the build sample is valid against the BTH extension definition
        """
        tile_set = self.build_tileset_sample()
        string_json_tile_set = tile_set.to_json()
        json_tile_set = json.loads(string_json_tile_set)

        if not self.schemas.validate("Tileset", json_tile_set):
            print('json_tile_set is not valid against the schema')
            self.fail()

    def unmature_test_tileset_build_sample_and_compare_reference_file(self):
        """
        Build the sample, load the version from the reference file and
        compare them (in memory as opposed to "diffing" files)
        """
        bt = self.build_bt_sample()
        string_json_bt = bt.to_json()
        json_bt = json.loads(string_json_bt)

        json_reference = self.test_load_reference_file()

        if not json_bt.items() == json_reference.items():
            self.fail()

if __name__ == "__main__":
    unittest.main()
