# -*- coding: utf-8 -*-

import json


class ThreeDTilesNotion(object):
    """
    One the 3DTiles notions defined as an abstract data model through 
    a schema of the 3DTiles specifications (either core of extensions).
    """

    def __init__(self):
        self.header = dict()

    def add_property_from_array(self, propertyName, array):
        self.header[propertyName] = array

    def to_json(self):
        return json.dumps(self.header, separators=(',', ':'))
