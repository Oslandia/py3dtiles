# -*- coding: utf-8 -*-

import os
import json
import unittest
from py3dtiles import BoundingVolume, HelperTest


class Test_Bounding_Volume(unittest.TestCase):

    def test_basics(self):
        helper = HelperTest(lambda x: BoundingVolume().validate(x))
        helper.sample_file_names.extend(['bounding_volume_box_sample.json',
                                         'bounding_volume_region_sample.json'])
        if not helper.check():
            self.fail()

    def build_sample(self):
        bounding_volume = BoundingVolume()
        bounding_volume.add_property_from_array(
                                   "box",
                                   [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        return bounding_volume

    def test_json_encoding(self):
        return self.build_sample().to_json()

    def test_build_bounding_volume_sample_and_validate(self):
        if not self.build_sample().validate():
            self.fail()

if __name__ == "__main__":
    unittest.main()
