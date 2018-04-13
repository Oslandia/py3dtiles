# -*- coding: utf-8 -*-

import numpy as np
import json


class BatchTable(object):
    """
    Only the JSON header has been implemented for now. According to the batch
    table documentation, the binary body is useful for storing long arrays of
    data (better performances)
    """

    def __init__(self):
        self.header = {}
        self.classToIndex = {}

    def add_property_from_array(self, propertyName, array):
        self.header[propertyName] = array

    # Hierarchy functions
    def _init_hierarchy(self):
        self.header['HIERARCHY'] = {
            'classes': [],
            'instancesLength': 0,
            'classIds': [],
            'parentCounts': [],
            'parentIds': []
        }

    # propertyNames: array of strings
    def add_class(self, name, propertyNames):
        if 'HIERARCHY' not in self.header:
            self._init_hierarchy()
        self.header['HIERARCHY']['classes'].append({
            'name': name,
            'length': 0,
            'instances': {propertyName: [] for propertyName in propertyNames}
        })
        self.classToIndex[name] = len(self.classToIndex)

    # properties: dictionnary with the same attributes as class instances
    # parent indices refers to the index of the parent in the batch table
    def add_class_instance(self, className, properties, parentIndices):
        idx = self.classToIndex[className]
        myClass = self.header['HIERARCHY']['classes'][idx]
        myClass['length'] += 1
        for i in myClass['instances']:
            myClass['instances'][i].append(properties[i])
        self.header['HIERARCHY']['instancesLength'] += 1
        self.header['HIERARCHY']['classIds'].append(idx)
        self.header['HIERARCHY']['parentCounts'].append(len(parentIndices))
        self.header['HIERARCHY']['parentIds'].extend(parentIndices)


    # returns batch table as binary
    def to_array(self):
        # convert dict to json string
        bt_json = json.dumps(self.header, separators=(',', ':'))
        # header must be 4-byte aligned (refer to batch table documentation)
        bt_json += ' '*(4 - len(bt_json) % 4)
        # returns an array of binaries representing the batch table
        return np.fromstring(bt_json, dtype=np.uint8)
