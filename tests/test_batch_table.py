# -*- coding: utf-8 -*-

import json
import unittest
from py3dtiles import BatchTable, ExtensionSet


class Test_Batch(unittest.TestCase):

    def setUp(self):
        self.extensions = ExtensionSet()
        file_name = 'py3dtiles/jsonschemas/batchTable.schema.json'
        try:
            self.extensions.append_extension_from_file(file_name)
        except:
            print(f'Unable to define extension {file_name}')
            self.fail()

    def tearDown(self):
        self.extensions.delete_extensions()

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
        if not self.extensions.validate("Batch Table", json_reference):
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

    def test_bt_build_sample_and_validate(self):
        """
        Assert the build sample is valid against the BTH extension definition
        """
        bt = Test_Batch.build_bt_sample()
        string_json_bt = bt.to_json()
        json_bt = json.loads(string_json_bt)

        if not self.extensions.validate("Batch Table", json_bt):
            print('json_bt is not valid against the schema')
            self.fail()

    def test_bt_build_sample_and_compare_reference_file(self):
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