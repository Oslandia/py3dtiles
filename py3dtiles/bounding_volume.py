# -*- coding: utf-8 -*-
import sys
from py3dtiles import ThreeDTilesNotion

class BoundingVolume(ThreeDTilesNotion):

    def __init__(self):
        super().__init__()
        # Because this is oneOf the following, implementation is simpler
        # without defining the following entries:
        # self.header["box"]
        # self.header["region"]
        # self.header["sphere"]

    def set(self, volume_type, array):
        if not (volume_type == "box"    or
                volume_type == "region" or
                volume_type == "sphere"):
            print(f'Erroneous volume type {volume_type}')
            sys.exit(1)
        self.header[volume_type] = array

    def assert_model_is_valid(self):
        defined = 0
        if "box" in self.header:
            defined += 1
            if not len(self.header["box"]) == 12:
                print("A box BoundingVolume must have eactly 12 items.")
                sys.exit(1)
        if "region" in self.header:
            defined += 1
            if not len(self.header["region"]) == 6:
                print("A region BoundingVolume must have eactly 6 items.")
                sys.exit(1)
        if "sphere" in self.header:
            defined += 1
            if not len(self.header["sphere"]) == 4:
                print("A sphere BoundingVolume must have eactly 4 items.")
                sys.exit(1)
        if not defined == 1:
            print("BoundingVolumes must have a box, a region or a sphere")
            sys.exit(1)

    def to_json(self):
        self.assert_model_is_valid()
        return super().to_json()
