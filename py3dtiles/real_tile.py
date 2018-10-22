# -*- coding: utf-8 -*-
from py3dtiles import ThreeDTilesNotion
from py3dtiles import BoundingVolume

class TileForReal(ThreeDTilesNotion):

    def __init__(self):
        super().__init__()
        self.header["boundingVolume"] = None
        # viewerRequestVolume
        self.header["geometricError"] = None
        # refine
        # self.header["transform"] = None

    def set_transform(self, transform):
        """
        :param transform: a flattened transformation matrix
        :return:
        """
        self.header["transform"] = [round(float(e), 3) for e in transform]

    def set_bounding_volume(self, bounding_volume):
        self.header["boundingVolume"] = bounding_volume

    def set_geometric_error(self, error):
        self.header["geometricError"] = error

    def prepare_for_json(self):
        if not self.header["boundingVolume"]:
            print("Warning: defaulting unset Tile boundingVolume")
            # FIXME: what would be a decent default ?!
            self.header["boundingVolume"] = BoundingVolume()
        if not self.header["geometricError"]:
            print("Warning: defaulting unset Tile boundingVolume")
            # FIXME: what would be a decent default ?!
            self.set_geometric_error(1000000.0)