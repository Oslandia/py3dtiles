import numpy as np

from .distance_test import is_point_far_enough, xyz_to_key


def is_point_far_enough_py(points, tested_point, squared_min_distance):
    for pt in points:
        if np.sum((tested_point - pt)**2) < squared_min_distance:
            return False
    return True


def are_point_far_enough(points, tested, index, dist):
    in_progress = []
    result = []
    for i in range(len(tested)):
        if i not in index:
            continue
        if True or len(points) == 0 or is_point_far_enough(points, tested[i], dist):
            if True or is_point_far_enough_py(in_progress, tested[i], dist):
                result += [i]
                in_progress += [tested[i]]

    return result


class CellNumpy(object):
    """docstring for CellNumpy"""

    def __init__(self, spacing):
        super(CellNumpy, self).__init__()
        self.sq_spacing = spacing * spacing
        self.count = 0
        self.storage = [
            np.zeros((16, 3), dtype='float32'),
            np.zeros((16, 3), dtype='uint8')
        ]

    def is_point_far_enough(self, xyz):
        if self.count == 0:
            return True
        valid_points = self.storage[0][0:self.count]
        return is_point_far_enough(
            valid_points,
            xyz,
            self.sq_spacing)

    def test_points(self, xyz, index):
        return are_point_far_enough(
            self.storage[0][0:self.count],
            xyz,
            index,
            self.sq_spacing)

    def insert(self, xyz, rgb):
        if self.count == self.storage[0].shape[0]:
            new_shape = (self.count * 2, 3)
            self.storage[0] = np.resize(self.storage[0], new_shape)
            self.storage[1] = np.resize(self.storage[1], new_shape)

        self.storage[0][self.count] = xyz
        self.storage[1][self.count] = rgb
        self.count += 1

    def insert_all(self, xyz, rgb):
        if (self.count + len(xyz)) > self.storage[0].shape[0]:
            new_shape = (self.count + len(xyz), 3)
            self.storage[0] = np.resize(self.storage[0], new_shape)
            self.storage[1] = np.resize(self.storage[1], new_shape)

        self.storage[0][self.count:self.count + len(xyz)] = xyz
        self.storage[1][self.count:self.count + len(xyz)] = rgb
        self.count += len(xyz)


class Grid(object):
    """docstring for Grid"""

    def __init__(self, node):
        super(Grid, self).__init__()
        self.cell_size = np.floor((node.aabb[1] - node.aabb[0]) / (node.spacing * 5.0)).astype(np.float32)
        self.cells = {}

    def insert(self, node, xyz, rgb):
        keys = xyz_to_key(xyz, self.cell_size, node.aabb[0], node.inv_aabb_size)

        if False:
            inserted = np.zeros(len(xyz))
            uniques = np.unique(keys)
            print(len(uniques))
            for key in uniques:
                if key not in self.cells:
                    self.cells[key] = CellNumpy(node.spacing)

                points_index = np.argwhere((keys - key) == 0)
                accepted = self.cells[key].test_points(xyz, points_index)
                if accepted:
                    yes = np.take(xyz, accepted, axis=0)
                    no = np.take(rgb, accepted, axis=0)

                    print('accepted {} on {}'.format(len(accepted), len(points_index)))
                    self.cells[key].insert_all(yes, no)

                    for i in accepted:
                        inserted[i] = 1
        else:
            inserted = np.ones(len(xyz))
            for i in range(0, len(xyz)):
                k = keys[i]
                if k not in self.cells:
                    self.cells[k] = CellNumpy(node.spacing)
                    self.cells[k].insert(xyz[i], rgb[i])
                elif self.cells[k].is_point_far_enough(xyz[i]):
                    self.cells[k].insert(xyz[i], rgb[i])
                else:
                    inserted[i] = 0

        indices = np.where(inserted)
        return (np.delete(xyz, indices, axis=0), np.delete(rgb, indices, axis=0))

    def get_point_count(self):
        s = 0
        for c in self.cells.values():
            s += c.count
        return s

    def get_points(self):
        xyz = ()
        rgb = ()
        pt = 0
        for k in self.cells:
            cell = self.cells[k]
            xyz += ((cell.storage[0][0:cell.count]).view(np.uint8).flatten(),)
            rgb += (cell.storage[1][0:cell.count].flatten(),)
            pt += cell.count
        res = np.concatenate((np.concatenate(xyz), np.concatenate(rgb)))
        assert len(res) == pt * (3 * 4 + 3)
        return res
