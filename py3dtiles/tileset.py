# -*- coding: utf-8 -*-


class TileSet:

    def __init__(self):
        self.asset = {"version": "1.0", "gltfUpAxis": "Z"}
        self.geometric_error = None
        self.root = dict()

    def set_transform(self, transform):
        """
        :param transform: a flattened transformation matrix
        :return:
        """
        self["root"]["transform"] = [round(float(e), 3) for e in transform]

    def set_geometric_error(self, error):
        self.geometric_error = error