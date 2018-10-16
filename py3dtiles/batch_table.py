# -*- coding: utf-8 -*-

import sys
import copy
import numpy as np
import json


class BatchTable(object):
    """
    Only the JSON header has been implemented for now. According to the batch
    table documentation, the binary body is useful for storing long arrays of
    data (better performances)
    """

    def __init__(self):
        self.header = dict()
        self.extensions = list()

    def add_property_from_array(self, propertyName, array):
        self.header[propertyName] = array

    def add_extension(self, extension, extension_set=None):
        extension_name = extension.get_extension_name()
        if extension_set and not extension_name in extension_set:
            print('Unkown extension {extension_name}.')
            sys.exit(1)
        self.extensions.append(extension)

    def to_array(self):
        """
        Returns the batch table represented as a binary
        """
        # convert dict to json string
        bt_json = json.dumps(self.header, separators=(',', ':'))
        # header must be 4-byte aligned (refer to batch table documentation)
        bt_json += ' '*(4 - len(bt_json) % 4)
        # returns an array of binaries representing the batch table
        return np.fromstring(bt_json, dtype=np.uint8)

    def to_json(self):
        """
        Convert to json string possibly including known extensions
        """
        # We don't want to be intrusive on self.header in case the object
        # will be further modified. We hence (deep) copy it. Note that if
        # (when?) memory footprint becomes an issue, we could also
        #   1. temporarily add an extensions key to self.header
        #   2. paste the json.dumps of the existing (self.)extensions to that
        #      extensions dictionary entry
        #   3. call json.dumps() on self.header
        #   4. delete the temporary self.header['extensions'] in order to
        #      retrieve the original self.header
        header = copy.deepcopy(self.header)
        if self.extensions:
            header['extensions'] = dict()
            for extension in self.extensions:
                header['extensions'][extension.get_extension_name()] = \
                                      copy.deepcopy(extension.hierarchy_root)
        return json.dumps(header, separators=(',', ':'))
