import numpy as np
# import lzma
import py3dtiles
import pickle
import os
import uuid
import time
import json

from .utils import name_to_filename, node_from_name, SubdivisionType, aabb_size_to_subdivision_type
from .points_grid import Grid
from .distance_test import xyz_to_child_index


class Node(object):
    """docstring for Node"""
    def __init__(self, name, aabb, spacing):
        super(Node, self).__init__()
        self.name = name
        self.aabb = aabb.astype(np.float32)
        self.aabb_size = (aabb[1] - aabb[0]).astype(np.float32)
        self.inv_aabb_size = (1.0 / self.aabb_size).astype(np.float32)
        self.aabb_center = ((aabb[0] + aabb[1]) * 0.5).astype(np.float32)
        self.spacing = spacing
        self.pending_xyz = []
        self.pending_rgb = []
        self.children = None
        self.grid = Grid(self)
        self.serialized_at = None
        self.points = [
            np.zeros((0, 3), dtype='float32'),
            np.zeros((0, 3), dtype='uint8'),
            0]
        self.dirty = False


    def save_to_bytes(self):
        sub_pickle = { }
        if self.children is not None:
            sub_pickle['children'] = self.children
            sub_pickle['grid'] = self.grid
        else:
            sub_pickle['points'] = self.points

        d = pickle.dumps(sub_pickle)
        return d
        # f = lzma.compress(d)
        # return f

        os.rename(t.name, filename)

        if False:
            check = Node(self.name, self.aabb, self.spacing)
            check.load_from_disk(filename)

            if self.children is not None:
                assert len(check.children) == len(self.children)
                for i in range(len(self.children)):
                    assert self.children[i] == check.children[i]
                for i in self.grid.cells:
                    assert self.grid.cells[i].count == check.grid.cells[i].count

    def load_from_bytes(self, byt):
        content = None

        sub_pickle = pickle.loads(byt) # lzma.decompress(byt))
        if 'children' in sub_pickle:
            self.children = sub_pickle['children']
            self.grid = sub_pickle['grid']
        else:
            self.points = sub_pickle['points']

    def insert(self, node_catalog, xyz, rgb, make_empty_node = False):
        if make_empty_node:
            self.pending_xyz += [xyz]
            self.pending_rgb += [rgb]
            return

        # fastpath
        if self.children is None:
            # print('fastpath for {}. Adding {} points'.format(self.name, len(xyz)))
            # count = points_storage.put(self.points, xyz, rgb)
            if self.points[2] + len(xyz) > len(self.points[0]):
                self.points[0] = np.resize(self.points[0], (self.points[2] + len(xyz), 3))
                self.points[1] = np.resize(self.points[1], (self.points[2] + len(xyz), 3))
            self.points[0][self.points[2]:self.points[2] + len(xyz)] = xyz
            self.points[1][self.points[2]:self.points[2] + len(xyz)] = rgb
            self.points[2] += len(xyz)

            if self.points[2] >= 20000 and self.spacing > 0.001:
                # print('split {}'.format(self.name))
                self.split(node_catalog)
                # print('splitted {}. In grid : {} (total: {}, pending: {})'.format(self.name, self.grid.get_point_count(), count, len(self.pending_xyz[0])))

            self.dirty = True

            return True
        # print('slowpath for {}. Adding {} points'.format(self.name, len(xyz)))
        # grid based insertion
        reminder = self.grid.insert(self, xyz, rgb)

        self.dirty = self.dirty or (len(reminder[0]) != len(xyz))

        if len(reminder) > 0:
            self.pending_xyz += [reminder[0]]
            self.pending_rgb += [reminder[1]]

    def write_pending_to_disk(self, folder, node_catalog, write_on_disk, max_depth, depth = 0):
        result = []

        if len(self.pending_xyz) > 0:
            assert depth == max_depth

            t = aabb_size_to_subdivision_type(self.aabb_size)
            for i in range(0, len(self.pending_xyz)):
                if len(self.pending_xyz[i]) == 0:
                    continue

                indices = xyz_to_child_index(self.pending_xyz[i], self.aabb_center)
                if t == SubdivisionType.QUADTREE:
                    # map upper z to lower z
                    indices = [u & 0xfe for u in indices]

                uniques = np.unique(indices)

                # make sure all children nodes exist
                for unique_key in uniques:
                    name = '{}{}'.format(self.name, unique_key)

                    # create missing nodes, only for remembering they exist.
                    # We don't want to serialize them
                    # probably not needed...
                    if name not in self.children:
                        self.children += [name]
                        self.dirty = True
                        # print('Added node {}'.format(name))

                    # group by indices
                    points_index = np.argwhere(indices - unique_key == 0)

                    assert points_index.size > 0

                    points_index = points_index.reshape(points_index.size)
                    xyz = np.take(self.pending_xyz[i], points_index, axis=0)
                    rgb = np.take(self.pending_rgb[i], points_index, axis=0)

                    d = pickle.dumps({ 'xyz': xyz, 'rgb': rgb })

                    if write_on_disk:
                        filename = '{}/{}.{}.npz'.format(folder, name, uuid.uuid4())
                        with open(filename, 'wb') as f:
                            f.write(d)
                        result += [(name, filename, len(xyz))]
                    else:
                        result += [(name, d, len(xyz))]

            self.pending_xyz = []
            self.pending_rgb = []
            return result
        elif self.children is not None and depth < max_depth:
            # then flush children
            for name in self.children:
                result += node_catalog.get(name).write_pending_to_disk(
                    folder,
                    node_catalog,
                    write_on_disk,
                    max_depth,
                    depth + 1)

        return result

    def split(self, node_catalog):
        start = time.perf_counter()
        self.children = []
        points = self.points # points_storage.get(self.name)
        # for i in range(0, points[2]):
        self.insert(node_catalog, points[0][0:points[2]], points[1][0:points[2]])
        self.points = None # points_storage.remove(self.name)

    def get_point_count(self, node_catalog, max_depth, depth = 0):
        if self.children is None:
            # print('{} : {}'.format(self.name, self.points))
            return self.points[2]
        else:
            count = self.grid.get_point_count()
            if depth < max_depth:
                for n in self.children:
                    count += node_catalog.get(n).get_point_count(
                        node_catalog, max_depth, depth + 1)
            return count

    # def to_tileset(self, node_catalog, folder, scale):
    #     # Se're working we unscaled / unoffsetted coordinates,
    #     # so there's no need to apply the inverse transform
    #     # from the tileset
    #     self.grid = None
    #     self.points = None

    #     print('{} x {} x {}'.format(100, self.spacing, scale[0]))
    #     center = self.aabb_center.tolist()
    #     tile = {
    #         'boundingVolume': {
    #             'box': [ center[0], center[1], center[2],
    #                 self.aabb_size[0] * 0.5, 0, 0,
    #                 0, self.aabb_size[1] * 0.5, 0,
    #                 0, 0, self.aabb_size[2] * 0.5]
    #         },
    #         'geometricError': (100 * self.spacing * scale[0]) if self.children is not None else 0.0,
    #     }

    #     ondisk_tile = name_to_filename(folder, self.name, '.pnts')
    #     if os.path.exists(ondisk_tile):
    #         tile['content'] = { 'url': os.path.relpath(ondisk_tile, folder) }

    #     if self.children is not None:
    #         children = self.children
    #         node_catalog.nodes.pop(self.name, None)

    #         tile['children'] = [node_catalog.get(k).to_tileset(node_catalog, folder, scale) for k in self.children]

    #     return tile

    @staticmethod
    def get_points(data):
        if data.children is None:
            points = data.points
            xyz = points[0][0:points[2]].view(np.uint8).flatten()
            rgb = points[1][0:points[2]].flatten()

            result = np.concatenate((xyz, rgb))
            assert len(result) == points[2] * (3 * 4 + 3)
            return result
        else:
            return data.grid.get_points()

    @staticmethod
    def to_tileset(name, parent_aabb, parent_spacing, folder, scale):
        # Se're working we unscaled / unoffsetted coordinates,
        # so there's no need to apply the inverse transform
        # from the tileset
        node = node_from_name(name, parent_aabb, parent_spacing)

        # center = ((ma + mi) * 0.5).tolist()
        center = node.aabb_center.tolist()
        tile = {
            'boundingVolume': {
                'box': [ center[0], center[1], center[2],
                    node.aabb_size[0] * 0.5, 0, 0,
                    0, node.aabb_size[1] * 0.5, 0,
                    0, 0, node.aabb_size[2] * 0.5]
            },
            # geometricError is in meter so cancel scale
            'geometricError': 10 * node.spacing / scale[0],
        }

        ondisk_tile = name_to_filename(folder, name, '.pnts')
        if os.path.exists(ondisk_tile):
            tile['content'] = { 'url': os.path.relpath(ondisk_tile, folder) }

        children = []
        for child in ['0', '1', '2', '3', '4', '5', '6', '7']:
            child_name = name + child
            ondisk_tile = name_to_filename(folder, child_name, '.pnts')
            if os.path.exists(ondisk_tile):
                children += [Node.to_tileset(child_name, node.aabb, node.spacing, folder, scale)]

        if children:
            tile['children'] = children
            # node ('') has no points,
            if len(name) == 0:
                tile['geometricError'] = np.linalg.norm(node.aabb_size) / scale[0],
        else:
            tile['geometricError'] = 0.0

        if len(name) > 0 and children:
            if len(json.dumps(tile)) > 100000:
                tile_root = {
                    'asset': {'version' : '1.0'},
                    'geometricError': tile['geometricError'],
                    'root' : tile
                }
                tileset_name = 'tileset.{}.json'.format(name)
                with open('{}/{}'.format(folder, tileset_name), 'w') as f:
                    f.write(json.dumps(tile_root))
                tile['content'] = { 'url': tileset_name }
                tile['children'] = []


        return tile
