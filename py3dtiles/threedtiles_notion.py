# -*- coding: utf-8 -*-
import json


class ThreeDTilesNotionBase(object):
    """
    One the 3DTiles notions defined as an abstract data model through 
    a schema of the 3DTiles specifications (either core of extensions).
    """

    def __init__(self):
        self.header = dict()

    def add_property_from_array(self, propertyName, array):
        self.header[propertyName] = array

    def prepare_for_json(self):
        return


class JSONEncoder(json.JSONEncoder):
    # The following constants are explained below (in the default method)
    telomere='@@@@'
    head = '"' + telomere
    tail = telomere + '"'

    def default(self, obj):
        if isinstance(obj, ThreeDTilesNotion):
            obj.prepare_for_json()
            # We only serialize the header part but with this very encoder
            # class in order to catch the other objects inheriting from
            # ThreeDTilesNotion
            result = json.dumps(obj.header,
                              separators=(',', ':'),
                              cls=JSONEncoder)
            # Because of the recursive dimension of the encoding (think of
            # what happens to a ThreeDTilesNotion being a member of another
            # ThreeDTilesNotion) we must avoid the undesirable side effects
            # of multiple encodings (and trouble begins with double encoding).
            # The difficulty is double:
            #  - first when the json encoder encounters a double quote within a
            #    string it will escape it (that is json.dump('x "y" z') will
            #    output "x\"y\"z"
            #  - second when given a string as input the json encoder will
            #    output that string enclosed in double quotes (that is
            #    json.dump('xyz') will output "xyz" (i.e. a five character
            #    string starting and ending with a double-quote and that could
            #    be annotated is this text as '"xyz"').
            # The above difficulties as well as the resolution (among others)
            # encoded below is best illustrated by the
            #    multiple_json_encoding_issue()
            # function encountered in this file (invoked by the __main__)
            #
            # Fix the "internal double-quote" problem: remove the escaped
            # double-quotes that might have been produced by the above
            # invocation of json.dump()
            result = result.replace('\\', '')
            # Fix the "ending/trailing double-quote" problem: this is a two
            # steps method. The SECOND step is realized by the next line and
            # consists in removing the previously tagged (with the '@@@@'
            # string) heading/trailing double quotes.
            result = result.replace(JSONEncoder.head, '')
            result = result.replace(JSONEncoder.tail, '')
            # The following line is the FIRST step for fixing the
            # "ending/trailing double-quote" issue: because a possible further
            # invocation of json.dump() acting on the string result returned
            # by this encoding, tag this string with heading and trailing
            # "telomeres" (refer to https://en.wikipedia.org/wiki/Telomere )
            # i.e. the "telomere" string
            return JSONEncoder.telomere + result + JSONEncoder.telomere
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class ThreeDTilesNotion(ThreeDTilesNotionBase):
    def to_json(self):
        # This is the gateway to the serialization (as opposd to the above
        # JSONEncoder.default()) that will trap the serialization calls when
        # walking the considered ThreeDTilesNotion hierarchy. We thus must
        # have exactly the same curative code (i.e. remove the side effects
        # as opposed to preventing trouble by adding telomere) as for
        # JSONEncoder.default(). Yet we cannot seem to be able to avoid
        # repetition of the code and for the time we accept replication.
        # Yet refer to the above version for the comments...
        self.prepare_for_json()
        result = json.dumps(self.header,
                            separators=(',', ':'),
                            cls=JSONEncoder)
        result = result.replace('\\', '')
        result = result.replace(JSONEncoder.head, '')
        result = result.replace(JSONEncoder.tail, '')
        return result

def multiple_json_encoding_issue():
    import sys
    import os
    if sys.version_info[0] == 2:
        print("   " + os.path.basename(__file__) + " requires Python version 3")
        sys.exit(1)

    print("########## The raw outcome")
    not_encoded = {"name": [1, 2]}
    encoded_once = json.dumps(not_encoded)
    encoded_twice = json.dumps(encoded_once)
    encoded_thrice = json.dumps(encoded_twice)
    print("Encoded once:   ", encoded_once)
    print("Encoded twice:  ", encoded_twice)
    print("Encoded thrice: ", encoded_thrice)

    print("\n########## Fixing internal double quotes")
    encoded_once = json.dumps(not_encoded)
    encoded_twice = json.dumps(encoded_once).replace('\\', '')
    encoded_thrice = json.dumps(encoded_twice).replace('\\', '')
    print("Encoded once:   ", encoded_once)
    print("Encoded twice:  ", encoded_twice)
    print("Encoded thrice: ", encoded_thrice)

    print("\n########## Fixing heading and trailing double quotes")
    telomere = '@@@@@'
    head = telomere + '"'
    tail = '"' + telomere
    encoded_once = json.dumps(not_encoded)
    encoded_once_telomerized = telomere + encoded_once + telomere
    encoded_twice = json.dumps(encoded_once_telomerized)
    encoded_twice_detelomerized = encoded_twice.replace(head, '').replace(tail,
                                                                          '')
    encoded_thrice_telomerized = telomere +encoded_twice_detelomerized+ telomere
    encoded_thrice = json.dumps(encoded_thrice_telomerized)
    encoded_thrice_detelomerized = encoded_thrice.replace(head, '').replace(
        tail, '')
    print("Encoded once:   ", encoded_once)
    print("Encoded twice:  ", encoded_twice_detelomerized)
    print("Encoded thrice: ", encoded_thrice_detelomerized)

    print("\n########## Combining both fixes")
    encoded_once = json.dumps(not_encoded)
    encoded_once_telomerized = telomere + encoded_once + telomere
    encoded_twice = json.dumps(encoded_once_telomerized).replace('\\', '')
    encoded_twice_detelomerized = encoded_twice.replace(head, '').replace(tail,
                                                                          '')
    encoded_thrice_telomerized = telomere +encoded_twice_detelomerized+ telomere
    encoded_thrice = json.dumps(encoded_thrice_telomerized).replace('\\', '')
    encoded_thrice_detelomerized = encoded_thrice.replace(head, '').replace(
        tail, '')
    print("Encoded once:   ", encoded_once)
    print("Encoded twice:  ", encoded_twice_detelomerized)
    print("Encoded thrice: ", encoded_thrice_detelomerized)

if __name__ == "__main__":
    multiple_json_encoding_issue()