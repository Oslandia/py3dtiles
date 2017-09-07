# -*- coding: utf-8 -*-

import json

class BatchTable(object):

    """
    Only the JSON header has been implemented for now. According to the batch table
    documentation, the binary body is useful for storing long arrays of data
    (better performances)
    """

    header = {}

    def __init__(self):
        self.header = {}

    def add_property_from_array(self, propertyName, array):
        self.header[propertyName] = array
