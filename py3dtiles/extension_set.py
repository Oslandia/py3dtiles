# -*- coding: utf-8 -*-

import os
import sys
import json
import jsonschema

class ExtensionSet:
    """
    Dictionary holding the set of valid extensions as defined by a
    corresponding schema. The dictionary key is the name of the extension
    as encountered in the "title" property of the schema.
    """
    extensions = dict()

    @classmethod
    def append_extension_from_schema(cls, schema):
        """
        Register an extension
        :param schema: the schema (as python object often as a result of a
                       json.loads()) defining the extension to be added
                       the list of already registavailable extensions
        :return: None
        """
        try:
            title = schema['title']
        except:
            print('Schema argument misses a title. Dropping extension.')
            sys.exit(1)
        if title in ExtensionSet.extensions:
            print(f'Already present extension {title}.')
            print(f'WARNING: overwriting extension {title}.')
            del ExtensionSet.extensions[title]
        try:
            # In order to validate the schema itself we still need to
            # provide some dummy item
            dummy_item = \
            {
               "classes" : [],
                "instancesLength" : 0,
                "classIds" : [],
                "parentCounts" : [],
                "parentIds" : []
            }
            jsonschema.Draft4Validator(schema).validate(dummy_item)
        except jsonschema.exceptions.SchemaError:
            print('Invalid schema')
            sys.exit(1)
        ExtensionSet.extensions[title] = schema

    @classmethod
    def append_extension_from_file(cls, file_name):
        """
        Register an extension through a file (holding a schema)
        :return: None
        """
        if not os.path.isfile(file_name):
            print(f'No such file as {file_name}')
            sys.exit(1)
        try:
            schema = json.loads(open(file_name, 'r').read())
        except:
            print(f'Unable to parse schema held in {file_name}')
            sys.exit(1)
        cls.append_extension_from_schema(schema)

    @classmethod
    def validate(cls, extension_name, item):
        """
        Validate the provided item against the schema associated with the
        named extension.
        :param extension_name: the name of the concerned extension
        :param item: a python object (possibly a result of a json.loads())
        :return: Boolean
        """
        try:
            schema = ExtensionSet.extensions[extension_name]
        except:
            print(f'Undefined extension {extension_name}')
            return False
        try:
            jsonschema.Draft4Validator(schema).validate(item)
        except:
            title = schema['title']
            print(f'Invalid item for schema {title}')
            return False
        return True

    @classmethod
    def delete_extensions(cls):
        ExtensionSet.extensions = dict()