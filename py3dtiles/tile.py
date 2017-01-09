# -*- coding: utf-8 -*-

import struct
import numpy as np
from enum import Enum
from abc import ABC, abstractmethod

from .feature_table import FeatureTable, FeatureTableHeader, FeatureTableBody


class Tile(ABC):

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
        f = open(filename, 'bw')
        f.write(bytes(tile_arr))
        f.close()

    def sync(self):
        """
        Allow to synchronize headers with contents.
        """

        self.header.sync(self.body)


class TileType(Enum):

    UNKNWON = 0
    POINTCLOUD = 1


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
