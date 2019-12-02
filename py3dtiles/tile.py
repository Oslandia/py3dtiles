# -*- coding: utf-8 -*-

import numpy as np
from enum import Enum
from abc import ABC, abstractmethod


class TileContent(ABC):

    def __init__(self):
        self.header = None
        self.body = None

    def to_array(self):
        self.sync()
        header_arr = self.header.to_array()
        body_arr = self.body.to_array()
        return np.concatenate((header_arr, body_arr))

    def to_hex_str(self):
        arr = self.to_array()
        return " ".join("{:02X}".format(x) for x in arr)

    def save_as(self, filename):
        tile_arr = self.to_array()
        with open(filename, 'bw') as f:
            f.write(bytes(tile_arr))

    def sync(self):
        """
        Allow to synchronize headers with contents.
        """

        self.header.sync(self.body)


class TileType(Enum):

    UNKNWON = 0
    POINTCLOUD = 1
    BATCHED3DMODEL = 2


class TileHeader(ABC):
    @abstractmethod
    def from_array(self, array):
        pass

    @abstractmethod
    def to_array(self):
        pass

    @abstractmethod
    def sync(self, body):
        pass


class TileBody(object):
    @abstractmethod
    def to_array(self):
        pass
