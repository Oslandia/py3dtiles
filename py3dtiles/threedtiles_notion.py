# -*- coding: utf-8 -*-
import json
from py3dtiles import SchemaValidators


class ThreeDTilesNotion(object):
    """
    One the 3DTiles notions defined as an abstract data model through 
    a schema of the 3DTiles specifications (either core of extensions).
    """
    validators = None

    def __init__(self):
        if not ThreeDTilesNotion.validators:
            ThreeDTilesNotion.validators = SchemaValidators()
        self.header = dict()

    def add_property_from_array(self, propertyName, array):
        self.header[propertyName] = array

    def prepare_for_json(self):
        return

    def validate(self, item):
        """
        Validate the item (python object) against the json schema associated
        with the class derived from ThreeDTilesNotion
        :param item: a Python object either deserialized (typically through
                     a json.loads()) or build programmatically.
        :return: validate is a predicate
        """
        class_name_key = self.__class__.__name__
        validator = self.validators.get_validator(class_name_key)
        try:
            validator.validate(item)
        except:
            print(f'Invalid item for schema {class_name_key}')
            return False
        return True

    def to_json(self):
        class JSONEncoder(json.JSONEncoder):

            def default(self, obj):
                if isinstance(obj, ThreeDTilesNotion):
                    obj.prepare_for_json()
                    return obj.header
                # Let the base class default method raise the TypeError
                return json.JSONEncoder.default(self, obj)

        self.prepare_for_json()
        result = json.dumps(self.header,
                            separators=(',', ':'),
                            cls=JSONEncoder)
        return result