# -*- coding: utf-8 -*-

import json
import unittest
from py3dtiles import BatchTable


class Test_Batch(unittest.TestCase):

    def test_load_reference_file(self):
        try:
            reference_file = 'tests/data/batch_table_sample.json'
            json_reference = json.loads(open(reference_file, 'r').read())
            json_reference.pop('_comment', None)  # Drop the pesky "comment".
        except:
            print(f'Unable to parse reference file {reference_file}')
            self.fail()
        return json_reference

    def test_json_reference_sample(self):
        json_reference = self.test_load_reference_file()
        if not BatchTable().validate(json_reference):
            print('Invalid item')
            self.fail()

    @classmethod
    def build_bt_sample(cls):
        """
        Programmatically define the reference sample encountered in the
        Bath Table specification cf
        https://github.com/AnalyticalGraphicsInc/3d-tiles/blob/master/specification/TileFormats/BatchTable/README.md#json-header
        :return: the sample as BatchTable object.
        """
        bt = BatchTable()

        bt.add_property_from_array("id",
                                   ["unique id", "another unique id"])
        bt.add_property_from_array("displayName",
                                   ["Building name", "Another building name"])
        bt.add_property_from_array("yearBuilt",
                                   [1999, 2015])
        bt.add_property_from_array("address",
                            [{"street" : "Main Street", "houseNumber" : "1"},
                             {"street" : "Main Street", "houseNumber" : "2"}])
        return bt

    def test_json_encoding(self):
        self.build_bt_sample().to_json()

    def test_bt_build_sample_and_validate(self):
        """
        Assert the build sample is valid against the BTH extension definition
        """
        string_json_bt = self.build_bt_sample().to_json()
        json_bt = json.loads(string_json_bt)

        if not BatchTable().validate(json_bt):
            print('json_bt is not valid against the schema')
            self.fail()

    def test_bt_build_sample_and_compare_reference_file(self):
        """
        Build the sample, load the version from the reference file and
        compare them (in memory as opposed to "diffing" files)
        """
        string_json_bt = self.build_bt_sample().to_json()
        json_bt = json.loads(string_json_bt)

        json_reference = self.test_load_reference_file()

        if not json_bt.items() == json_reference.items():
            self.fail()

if __name__ == "__main__":
    unittest.main()