# -*- coding: utf-8 -*-

from py3dtiles import BatchTableHierarchy, ExtensionSet
from tests.test_batch_table import Test_Batch
import json
import unittest


class Test_BatchTableHierarchy(unittest.TestCase):
    """
    Batch Table Hierarchy (BTH) extension related tests
    """

    def setUp(self):
        self.extensions = ExtensionSet()
        file_name = 'py3dtiles/jsonschemas/3DTILES_batch_table_hierarchy.json'
        try:
            self.extensions.append_extension_from_file(file_name)
        except:
            print(f'Unable to define extension {file_name}')
            self.fail()
        # We also need the classic Batch Table
        file_name = 'py3dtiles/jsonschemas/batchTable.schema.json'
        try:
            self.extensions.append_extension_from_file(file_name)
        except:
            print(f'Unable to define extension {file_name}')
            self.fail()

    def tearDown(self):
        self.extensions.delete_extensions()

    def test_json_sample(self):
        try:
            item_file = 'tests/data/batch_table_hierarchy_reference_sample.json'
            item = json.loads(open(item_file, 'r').read())
        except:
            print(f'Unable to parse item file {filename}')
            self.fail()
        if not \
            self.extensions.validate("3DTILES_batch_table_hierarchy extension",
                                     item):
            print('Invalid item')
            self.fail()

    def build_bth_sample(self):
        """
        Programmatically define the reference sample encountered in the
        BTH specification cf
        https://github.com/AnalyticalGraphicsInc/3d-tiles/tree/master/extensions/3DTILES_batch_table_hierarchy#batch-table-json-schema-updates
        :return: the sample as BatchTableHierarchy object.
        """
        bth = BatchTableHierarchy()

        bth.add_class("Wall", ["color"])
        bth.add_class_instance("Wall", {'color': 'white'},  [6])
        bth.add_class_instance("Wall", {'color': 'red'},    [6, 10,11])
        bth.add_class_instance("Wall", {'color': 'yellow'}, [7, 11])
        bth.add_class_instance("Wall", {'color': 'gray'},   [7])
        bth.add_class_instance("Wall", {'color': 'brown'},  [8])
        bth.add_class_instance("Wall", {'color': 'black'},  [8])

        bth.add_class("Building", ["name", "address"])
        bth.add_class_instance("Building", {'name': 'unit29',
                                            'address': '100 Main St'}, [10])
        bth.add_class_instance("Building", {'name': 'unit20',
                                            'address': '102 Main St'}, [10])
        bth.add_class_instance("Building", {'name': 'unit93',
                                            'address': '104 Main St'}, [9])

        bth.add_class("Owner", ["type", "id"])
        bth.add_class_instance("Owner", {'type': 'city',       'id': 1120})
        bth.add_class_instance("Owner", {'type': 'resident',   'id': 1250})
        bth.add_class_instance("Owner", {'type': 'commercial', 'id': 6445})
        return bth

    def test_bth_build_sample_and_validate(self):
        """
        Assert the build sample is valid against the BTH extension definition
        """
        bth = self.build_bth_sample()
        string_json_bth = bth.to_json()
        json_bth = json.loads(string_json_bth)

        if not self.extensions.validate("3DTILES_batch_table_hierarchy extension",
                                   json_bth):
            print('json_bth is not valid against the schema')
            self.fail()

    def test_bth_build_sample_and_compare_reference_file(self):
        """
        Build the sample, load the version from the reference file and
        compare them (in memory as opposed to "diffing" files)
        """
        bth = self.build_bth_sample()
        string_json_bth = bth.to_json()
        json_bth = json.loads(string_json_bth)

        reference_file = 'tests/data/batch_table_hierarchy_reference_sample.json'
        json_reference = json.loads(open(reference_file, 'r').read())
        json_reference.pop('_comment', None)  # Drop the pesky "comment" entry.
        if not json_bth.items() == json_reference.items():
            self.fail()

    def unmature_test_plug_extension_into_simple_batch_table(self):
        # it looks like the extensions entry within
        #       py3dtiles/jsonschemas/batchTable.schema.json
        # that points to a generic extension "extension.schema.json" is not
        # used by the validator (renaming that entry or removing the
        # "extension.schema.json" file doesn't change the behavior of the
        # validator...
        bt = Test_Batch.build_bt_sample()
        bth = self.build_bth_sample()
        bt.add_extension(bth)
        string_json_extended_bt = bt.to_json()
        json_extended_bt = json.loads(string_json_extended_bt)
        print("aaaaaaaaaaaaaaaaaaaaaaa", string_json_extended_bt)
        if not self.extensions.validate("Batch Table", json_extended_bt):
           print('Invalid item')
           self.fail()

if __name__ == "__main__":
    unittest.main()