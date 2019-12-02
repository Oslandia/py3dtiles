import numpy as np
import math
import traceback
import pyproj
import struct
from pickle import dumps as pdumps


def init(files, color_scale=None, srs_in=None, srs_out=None, fraction=100):
    aabb = None
    total_point_count = 0
    pointcloud_file_portions = []
    avg_min = np.array([0.0, 0.0, 0.0])

    for filename in files:
        try:
            f = open(filename, "r")
        except Exception as e:
            print("Error opening {filename}. Skipping.".format(**locals()))
            print(e)
            continue

        count = 0
        seek_values = []
        while True:
            batch = 10000
            points = np.zeros((batch, 3))

            offset = f.tell()
            for i in range(batch):
                line = f.readline()
                if not line:
                    points = np.resize(points, (i, 3))
                    break
                points[i] = [float(s) for s in line.split(" ")][:3]

            if points.shape[0] == 0:
                break

            if not count % 1000000:
                seek_values += [offset]

            count += points.shape[0]
            batch_aabb = np.array([
                np.min(points, axis=0), np.max(points, axis=0)
            ])

            # Update aabb
            if aabb is None:
                aabb = batch_aabb
            else:
                aabb[0] = np.minimum(aabb[0], batch_aabb[0])
                aabb[1] = np.maximum(aabb[1], batch_aabb[1])

        # We need an exact point count
        total_point_count += count * fraction / 100

        _1M = min(count, 1000000)
        steps = math.ceil(count / _1M)
        assert steps == len(seek_values)
        portions = [
            (i * _1M, min(count, (i + 1) * _1M), seek_values[i]) for i in range(steps)
        ]
        for p in portions:
            pointcloud_file_portions += [(filename, p)]

        if srs_out is not None and srs_in is None:
            raise Exception(
                "'{}' file doesn't contain srs information. Please use the --srs_in option to declare it.".format(
                    filename
                )
            )

    return {
        "portions": pointcloud_file_portions,
        "aabb": aabb,
        "color_scale": color_scale,
        "srs_in": srs_in,
        "point_count": total_point_count,
        "avg_min": aabb[0],
    }


def run(_id, filename, offset_scale, portion, queue, projection, verbose):
    """
    Reads points from a xyz file

    Consider XYZIRGB format following FME documentation(*). If the number of
    features does not correspond (i.e. does not equal to 7), we do the
    following hypothesis:
    - 3 features mean XYZ
    - 4 features mean XYZI
    - 6 features mean XYZRGB

    (*) See: https://docs.safe.com/fme/html/FME_Desktop_Documentation/FME_ReadersWriters/pointcloudxyz/pointcloudxyz.htm
    """
    try:
        f = open(filename, "r")

        point_count = portion[1] - portion[0]

        step = min(point_count, max((point_count) // 10, 100000))

        f.seek(portion[2])

        feature_nb = 7

        for i in range(0, point_count, step):
            points = np.zeros((step, feature_nb), dtype=np.float32)

            for j in range(0, step):
                line = f.readline()
                if not line:
                    points = np.resize(points, (j, feature_nb))
                    break
                line_features = [float(s) for s in line.split(" ")]
                if len(line_features) == 3:
                    line_features += [None] * 4  # Insert intensity and RGB
                elif len(line_features) == 4:
                    line_features += [None] * 3  # Insert RGB
                elif len(line_features) == 6:
                    line_features.insert(3, None)  # Insert intensity
                points[j] = line_features

            x, y, z = [points[:, c] for c in [0, 1, 2]]

            if projection:
                x, y, z = pyproj.transform(projection[0], projection[1], x, y, z)

            x = (x + offset_scale[0][0]) * offset_scale[1][0]
            y = (y + offset_scale[0][1]) * offset_scale[1][1]
            z = (z + offset_scale[0][2]) * offset_scale[1][2]

            coords = np.vstack((x, y, z)).transpose()

            if offset_scale[2] is not None:
                # Apply transformation matrix (because the tile's transform will contain
                # the inverse of this matrix)
                coords = np.dot(coords, offset_scale[2])

            coords = np.ascontiguousarray(coords.astype(np.float32))

            # Read colors: 3 last columns of the point cloud
            colors = points[:, -3:].astype(np.uint8)

            queue.send_multipart(
                [
                    "".encode("ascii"),
                    pdumps({"xyz": coords, "rgb": colors}),
                    struct.pack(">I", len(coords)),
                ],
                copy=False,
            )

        queue.send_multipart([pdumps({"name": _id, "total": 0})])
        # notify we're idle
        queue.send_multipart([b""])

        f.close()
    except Exception as e:
        print("Exception while reading points from xyz file")
        print(e)
        traceback.print_exc()
