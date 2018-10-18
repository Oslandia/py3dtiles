# -*- coding: utf-8 -*-

import os
import sys
import json
import jsonschema

class ExtensionSet:
    """
    Dictionary holding the set of validated schemas. The dictionary key is
    the name of the schema as encountered in the "title" property of the schema.
    """
    schemas = dict()
    resolver = None

    @classmethod
    def get_dummy_item(cls, title):
        """
        Retrieve a dummy (as simple as possible to validate) json item
        corresponding to the title
        :param title: the title (i.e. the header name "title" within the
                      schema) of the designated schema.
        :return: the constructed dummy json item
        """
        if title == "3DTILES_batch_table_hierarchy extension":
            return \
            {
                "classes" : [],
                "instancesLength" : 0,
                "classIds" : [],
                "parentCounts" : [],
                "parentIds" : []
            }

        if title == "Batch Table":
            return { "ids":[1, 2] }

        if title == "Bounding Volume":
            return { "box": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]}

        if title == "Tileset":
            return \
            {
                "asset": {"version": "1.0" },
                "geometricError": 3.14159,
                "root": {
                    "boundingVolume": {
                        "box": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
                    },
                    "geometricError": 3.14159
                }
            }
        return None
        #"box": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        #"region": [1, 2, 3, 4, 5, 6]

    @classmethod
    def append_schema_from_file(cls, file_name):
        """
        Register an extension
        :param file_name: file holding the schema to be added to the
                the list of already registered schemas
                Warning: when the schema uses references ($ref entries) to
                other external schemas, those schema must be encountered in the
                SAME directory as the scheme itself (otherwise the schema
                reference resolver has no clue on where to find the sub-schemas)
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

        try:
            title = schema['title']
        except:
            print('Schema argument misses a title. Dropping extension.')
            sys.exit(1)

        if title in ExtensionSet.schemas:
            print(f'Already present extension {title}.')
            print(f'WARNING: overwriting extension {title}.')
            del ExtensionSet.schemas[title]

        # Build a resolver that will look for (resolve) possible $ref
        # sub-schemas within the same directory (provided as absolute path)
        # as the given schema. Refer to
        #     https://github.com/Julian/jsonschema/issues/98
        # for the reasons of the following paramets and call
        base_uri = 'file://' + os.path.dirname(os.path.abspath(file_name)) + '/'
        resolver = jsonschema.RefResolver(base_uri, None)

        validator = jsonschema.Draft4Validator(schema, resolver = resolver)

        try:
            # In order to validate the schema itself we still need to
            # provide a dummy json item
            dummy_item = ExtensionSet.get_dummy_item(title)
            validator.validate(dummy_item)
        except jsonschema.exceptions.SchemaError:
            print(f'Invalid schema {title}')
            sys.exit(1)
        ExtensionSet.schemas[title] = {'schema': schema,
                                          'validator': validator}

    @classmethod
    def validate(cls, schema_name, item):
        """
        Validate the provided item against the schema associated with the
        named schema.
        :param schema_name: the name of the concerned schema
        :param item: a python object (possibly a result of a json.loads())
        :return: Boolean
        """
        if not schema_name in cls.schemas:
            print(f'Unregistered schema {schema_name}')
            return False
        try:
            validator = cls.schemas[schema_name]["validator"]
        except:
            print(f'Cannot find validator for schema {schema_name}')
            return False
        try:
            validator.validate(item)
        except:
            print(f'Invalid item for schema {schema_name}')
            return False
        return True

    @classmethod
    def __contains__(cls, schema_name):
        if schema_name in ExtensionSet.schemas:
            return True
        return False

    @classmethod
    def delete_schemas(cls):
        ExtensionSet.schemas = dict()