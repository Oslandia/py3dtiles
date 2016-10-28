#! /usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

from py3dtiles import TileReader


def print_info(filename):

    tile = TileReader().read_file(filename)

    # tile header
    th = tile.header
    print("Tile Header")
    print("-----------")
    print("Magic Value: ", th.magic_value)
    print("Version: ", th.version)
    print("Tile byte length: ", th.tile_byte_length)
    print("Feature table json byte length: ", th.ft_json_byte_length)
    print("Feature table bin byte length: ", th.ft_bin_byte_length)

    # feature table header
    fth = tile.body.feature_table.header
    print("")
    print("Feature Table Header")
    print("--------------------")
    print(fth.to_json())

    # first point data
    if fth.points_length > 0:
        print("")
        print("First point")
        print("-----------")
        f = tile.body.feature_table.feature(0)
        d = f.positions
        d.update(f.colors)
        print(d)

if __name__ == '__main__':
    # arg parse
    descr = 'Extract informations from a 3DTiles file'
    parser = argparse.ArgumentParser(description=descr)

    f_help = 'filename'
    parser.add_argument('f', metavar='f', type=str, help=f_help)

    args = parser.parse_args()

    print_info(args.f)
