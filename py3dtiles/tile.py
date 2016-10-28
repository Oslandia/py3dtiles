# -*- coding: utf-8 -*-

import struct
import numpy as np
from enum import Enum

from .feature_table import FeatureTable, FeatureTableHeader, FeatureTableBody


class Tile(object):

    def __init__(self):
        self.header = TileHeader()
        self.body = TileBody()

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

        # extract array
        fth_arr = self.body.feature_table.header.to_array()
        ftb_arr = self.body.feature_table.body.to_array()

        # sync the tile header with feature table contents
        self.header.magic_value = "pnts"
        self.header.tile_byte_length = len(fth_arr) + len(ftb_arr) + TileHeader.BYTELENGTH
        self.header.ft_json_byte_length = len(fth_arr)
        self.header.ft_bin_byte_length = len(ftb_arr)

    @staticmethod
    def from_features(pdtype, cdtype, features):
        """
        dtype : numpy.dtype
            Numpy description of a single feature

        features : Feature[]

        Returns
        -------
        tile : Tile
        """

        ft = FeatureTable.from_features(pdtype, cdtype, features)

        tb = TileBody()
        tb.feature_table = ft

        th = TileHeader()

        t = Tile()
        t.body = tb
        t.header = th

        return t

    @staticmethod
    def from_array(array):
        """
        Parameters
        ----------
        array : numpy.array

        Returns
        -------
        t : Tile
        """

        # build tile header
        h_arr = array[0:TileHeader.BYTELENGTH]
        h = TileHeader.from_array(h_arr)

        if h.tile_byte_length != len(array):
            raise RuntimeError("Invalid byte length in header")

        # build tile body
        b_len = h.ft_json_byte_length + h.ft_bin_byte_length
        b_arr = array[TileHeader.BYTELENGTH:TileHeader.BYTELENGTH+b_len]
        b = TileBody.from_array(h, b_arr)

        # build Tile with header and body
        t = Tile()
        t.header = h
        t.body = b

        return t


class TileType(Enum):

    UNKNWON = 0
    POINTCLOUD = 1


class TileHeader(object):

    BYTELENGTH = 28

    def __init__(self):
        self.type = TileType.UNKNWON
        self.magic_value = ""
        self.version = 1
        self.tile_byte_length = 0
        self.ft_json_byte_length = 0
        self.ft_bin_byte_length = 0
        self.bt_json_byte_length = 0
        self.bt_bin_byte_length = 0

    def to_array(self):
        header_arr = np.fromstring(self.magic_value, np.uint8)

        header_arr2 = np.array([self.version,
                                self.tile_byte_length,
                                self.ft_json_byte_length,
                                self.ft_bin_byte_length,
                                self.bt_json_byte_length,
                                self.bt_bin_byte_length], dtype=np.uint32)

        return np.concatenate((header_arr, header_arr2.view(np.uint8)))

    @staticmethod
    def from_array(array):
        """
        Parameters
        ----------
        array : numpy.array

        Returns
        -------
        h : TileHeader
        """

        h = TileHeader()

        if len(array) != TileHeader.BYTELENGTH:
            raise RuntimeError("Invalid header length")

        h.magic_value = bytes(array[0:4]).decode("utf-8")
        h.version = struct.unpack("i", array[4:8])[0]
        h.tile_byte_length = struct.unpack("i", array[8:12])[0]
        h.ft_json_byte_length = struct.unpack("i", array[12:16])[0]
        h.ft_bin_byte_length = struct.unpack("i", array[16:20])[0]
        h.bt_json_byte_length = struct.unpack("i", array[20:24])[0]
        h.bt_bin_byte_length = struct.unpack("i", array[24:28])[0]

        if h.magic_value == "pnts":
            h.type = TileType.POINTCLOUD

        return h


class TileBody(object):

    def __init__(self):
        self.feature_table = FeatureTable()
        # TODO : self.batch_table = BatchTable()

    def to_array(self):
        return self.feature_table.to_array()

    @staticmethod
    def from_array(th, array):
        """
        Parameters
        ----------
        th : TileHeader

        array : numpy.array

        Returns
        -------
        b : TileBody
        """

        # build feature table
        ft_len = th.ft_json_byte_length + th.ft_bin_byte_length
        ft_arr = array[0:ft_len]
        ft = FeatureTable.from_array(th, ft_arr)

        # build batch table
        # bt_len = th.bt_json_byte_length + th.bt_bin_byte_length
        # bt_arr = array[ft_len:ft_len+ba_len]
        # bt = BatchTable.from_array(th, bt_arr)

        # build tile body with feature table
        b = TileBody()
        b.feature_table = ft
        # b.batch_table = bt

        return b
