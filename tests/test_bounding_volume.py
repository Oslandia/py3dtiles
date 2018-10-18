# -*- coding: utf-8 -*-

import os
import json
import unittest
from py3dtiles import BoundingVolume, ExtensionSet


class Test_Bounding_Volume(unittest.TestCase):

    def setUp(self):
        self.schemas = ExtensionSet()
        file_name = 'py3dtiles/jsonschemas/boundingVolume.schema.json'
        try:
            self.schemas.append_schema_from_file(file_name)
        except:
            print(f'Unable to define extension {file_name}')
            self.fail()

    def tearDown(self):
        self.schemas.delete_schemas()

    def check_json_reference_sample(self, file_name):
        try:
            reference_file = os.path.join('tests/data', file_name)
            json_reference = json.loads(open(reference_file, 'r').read())
            json_reference.pop('_comment', None)  # Drop the pesky "comment".
        except:
            print(f'Unable to parse reference file {reference_file}')
            self.fail()
        return self.schemas.validate("Bounding Volume", json_reference)

    def test_json_references_samples(self):
        for file_name in {'bounding_volume_box_sample.json',
                          'bounding_volume_region_sample.json'}:
            if not self.check_json_reference_sample(file_name):
                print(f'Invalid BoundingVolume file {file_name}')
                self.fail()

    def build_bounding_volume_sample(cls):
        bounding_volume = BoundingVolume()
        bounding_volume.add_property_from_array(
                                   "box",
                                   [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        return bounding_volume

    def test_build_bounding_volume_sample_and_validate(self):
        """
        Assert the build sample is valid against the BTH extension definition
        """
        bounding_volume = self.build_bounding_volume_sample()
        string_json_bounding_volume = bounding_volume.to_json()
        json_bounding_volume = json.loads(string_json_bounding_volume)

        if not self.schemas.validate("Bounding Volume", json_bounding_volume):
            print('json_bounding_volume is not valid against the schema')
            self.fail()

if __name__ == "__main__":
    unittest.main()
