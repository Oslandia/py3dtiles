import numpy as np

#pythran export is_point_far_enough(float32[][], float32[], float)
def is_point_far_enough(points, tested_point, squared_min_distance):
    for i in range(len(points) - 1, 0, -1):
        if np.sum((points[i] - tested_point)**2) < squared_min_distance:
            return False
    return True
    # distance = np.sum((points - tested_point)**2, axis=1)
    # if np.min(distance) < squared_min_distance:
        # return False
    # return True


#pythran export xyz_to_child_index(float32[][], float32[])
def xyz_to_child_index(xyz, aabb_center):
    test = np.greater_equal(xyz - aabb_center, 0).astype(np.int8)
    shift = [2, 1, 0]
    return np.sum(np.left_shift(test, shift), axis=1)

#pythran export xyz_to_key(float32[][], float32[], float32[], float32[])
def xyz_to_key(xyz, cell_size, aabb_min, inv_aabb_size):
    a = np.floor(cell_size * (xyz - aabb_min) * inv_aabb_size)
    a = np.minimum(np.maximum(a, 0), cell_size).astype(np.int64)
    # 64 bits / 3 ~= 21 bits each
    return np.bitwise_or(
        np.bitwise_or(
            np.left_shift(a[:,0], 21 * 2), np.left_shift(a[:,1], 21)), a[:,2])
