# -*- coding: utf-8 -*-

import json


class BatchTableHierarchy(object):
    """
    Batch Table Hierarchy (BAH) is an Extension of a Batch Table.
    """

    def __init__(self):
        # The usage of properties whose name is prefixed with an
        # underscore are purely technical to this implementation
        # and are not part of the Batch Table Hierarchy (BAH)
        # specification.
        '''
        List of the _indexes_ of the class (types) used by this BAH.
        '''
        self._class_to_index = {}

        self.hierarchy_root = {
            'classes': [],
            'instancesLength': 0,
            'classIds': [],
            'parentCounts': [],
            'parentIds': []
        }

    def add_class(self, class_name, property_names):
        """
        :param class_name: the name of the class (as a type) to be defined
        :param property_names: array of strings holding the names of the
                              properties (attributes) defining this class
        :return: None
        """
        self.hierarchy_root['classes'].append({
            'name': class_name,
            'length': 0,
            'instances': {property_name: []
                          for property_name in property_names}})
        self._class_to_index[class_name] = len(self._class_to_index)

    # properties: dictionnary with the same attributes as class instances
    # parent indices refers to the index of the parent in the batch table
    def add_class_instance(self, class_name, properties, parent_indexes = []):
        """
        :param class_name: a class name of class (type) previously
                           defined with the add_class() method
        :param properties: dictionary with the same attributes as defined
                           in the class type (referred by class_name)
        :param parent_indexes: indexes of the parent(s)
        """
        index = self._class_to_index[class_name]
        my_class = self.hierarchy_root['classes'][index]
        my_class['length'] += 1
        for property in my_class['instances']:
            my_class['instances'][property].append(properties[property])
        self.hierarchy_root['instancesLength'] += 1
        self.hierarchy_root['classIds'].append(index)
        self.hierarchy_root['parentCounts'].append(len(parent_indexes))
        self.hierarchy_root['parentIds'].extend(parent_indexes)

    def to_json(self):
        # convert dict to json string
        return json.dumps(self.hierarchy_root, separators=(',', ':'))
