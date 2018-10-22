# -*- coding: utf-8 -*-
import os
import json


class HelperTest:
    def __init__(self):
        self.sample_file_names = list()

    @classmethod
    def load_json_reference_file(cls, filename):
        try:
            reference_file_path = os.path.join('tests/data', filename)
            with open(reference_file_path, 'r') as reference_file:
                json_reference = json.loads(reference_file.read())
            json_reference.pop('_comment', None)  # Drop the "comment".
        except:
            print(f'Unable to parse reference file {reference_file_path}')
            cls.fail()
        return json_reference

    def test_load_reference_files(self):
        for file_name in self.sample_file_names:
            self.load_json_reference_file(file_name)
