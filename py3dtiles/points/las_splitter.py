import numpy as np
import os
import time
import math
import traceback
import laspy
import pyproj
from memory_profiler import memory_usage

from .node import Node

def process_root_node(folder, filename, root_aabb, root_spacing, offset_scale, portion, queue, projection, verbose):
    '''
    Reads points from a las file, and either:
      - assign them to the root node of the octree
      - forward them to children nodes
    '''
    try:
        # print(">> CAS 1: {}".format(memory_usage(proc=os.getpid())))
        f = laspy.file.File(filename, mode='r')

        point_count = portion[1] - portion[0]

        step = min(point_count,
            max((point_count) // 10, 100000))
        # step = point_count
        indices = [i for i in range(math.ceil((point_count) / step))]

        root = Node('', root_aabb, root_spacing)

        file_points = f.get_points()['point']
        X = file_points['X']
        Y = file_points['Y']
        Z = file_points['Z']
        # todo: attributes
        if 'red' in f.point_format.lookup:
            RED = file_points['red']
            GREEN = file_points['green']
            BLUE = file_points['blue']
        else:
            RED = file_points['intensity']
            GREEN = file_points['intensity']
            BLUE = file_points['intensity']

        start = time.perf_counter()

        for index in indices:
            # print('{} %'.format(round(100 * indices.index(index) / len(indices), 1)))
            if root.children is None:
                root.children = []

            loop_start = time.perf_counter()

            start_offset = portion[0] + index * step
            num = min(step, portion[1] - start_offset)

            # read scaled values and apply offset
            x = X[start_offset:start_offset + num] * f.header.scale[0] + f.header.offset[0]
            y = Y[start_offset:start_offset + num] * f.header.scale[1] + f.header.offset[1]
            z = Z[start_offset:start_offset + num] * f.header.scale[2] + f.header.offset[2]

            if projection:
                x, y, z = pyproj.transform(projection[0], projection[1], x, y, z)

            x = (x + offset_scale[0][0]) * offset_scale[1][0]
            y = (y + offset_scale[0][1]) * offset_scale[1][1]
            z = (z + offset_scale[0][2]) * offset_scale[1][2]

            coords = np.vstack((x, y, z)).transpose()

            if offset_scale[2] is not None:
                # Apply transformation matrix (because the tile's transform will contain
                # the inverse of this matrix)
                coords = np.dot(coords, offset_scale[2])
                # for i in range(len(coords)):
                #     coords[i] = np.dot(coords[i], offset_scale[2])

            coords = coords.astype(np.float32)

            # Read colors
            red = RED[start_offset:start_offset + num]
            green = GREEN[start_offset:start_offset + num]
            blue = BLUE[start_offset:start_offset + num]
            colors = np.vstack((red, green, blue)).transpose()
            # insert in level 0 node:
            #   - children are not created
            #   - points that don't fit in root are stored in pending
            root.insert(None, coords, colors, True)

            # affect pending points to children:
            #   - create children (so when we serialize root, we'll remember that we have children)
            #   - clear pending
            #   - write .npz files, named after the child they belong to
            result = root.write_pending_to_disk(folder, None, True, 0)

            for r in result:
                queue.put(r)

        f.close()
        # print("<< CAS 1: {}".format(memory_usage(proc=os.getpid())))

        # Serialize root to disk. We only want to save:
        #  - its internal points (node.points or node.grid)
        #  - its children names
        # print('Save root on disk {}'.format(node_catalog.get('').children))
        # node_catalog.save_on_disk('', False, 0, 0)
    except Exception as e:
        print('OOPS root')
        print(e)
        traceback.print_exc()
