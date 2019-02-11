# -*- coding: utf-8 -*-
import struct
import math
from .earcut import earcut
import numpy as np
import json
from shapely.geometry import Point, Polygon


class GlTF(object):

    def __init__(self):
        self.header = {}
        self.body = None

    def to_array(self):  # bgl
        scene = json.dumps(self.header, separators=(',', ':'))

        # scene = struct.pack(str(len(scene)) + 's', scene.encode('utf8'))
        # body must be 4-byte aligned
        scene += ' '*(4 - len(scene) % 4)

        binaryHeader = np.fromstring("glTF", dtype=np.uint8)
        binaryHeader2 = np.array([1,
                                  20 + len(self.body) + len(scene),
                                  len(scene),
                                  0], dtype=np.uint32)

        return np.concatenate((binaryHeader,
                               binaryHeader2.view(np.uint8),
                               np.fromstring(scene, dtype=np.uint8),
                               self.body))

    @staticmethod
    def from_array(array):
        """
        Parameters
        ----------
        array : numpy.array

        Returns
        -------
        glTF : GlTf
        """

        glTF = GlTF()

        if struct.unpack("4s", array[0:4])[0] != b"glTF":
            raise RuntimeError("Array does not contain a binary glTF")

        if struct.unpack("i", array[4:8])[0] != 1:
            raise RuntimeError("Unsupported glTF version")

        length = struct.unpack("i", array[8:12])[0]
        content_length = struct.unpack("i", array[12:16])[0]

        if struct.unpack("i", array[16:20])[0] != 0:
            raise RuntimeError("Unsupported binary glTF content type")

        header = struct.unpack(str(content_length) + "s",
                               array[20:20+content_length])[0]
        glTF.header = json.loads(header.decode("ascii"))
        glTF.body = array[20+content_length:length]

        return glTF

    @staticmethod
    def from_wkb_as_lines(wkbs, bboxes, transform, binary=True, batched=True, uri=None):
        """
        Parameters
        ----------
        wkbs : array
            Array of wkbs

        bboxes : array
            Array of bounding boxes (numpy.array)

        transform : numpy.array
            World coordinates transformation flattend matrix

        Returns
        -------
        glTF : GlTF
        """

        glTF = GlTF()
        nodes = []

        bb = []
        for wkb, bbox in zip(wkbs, bboxes):
            mp = parse_to_lines(bytes(wkb))

            nodes.append(mp)
            bb.append(bbox)

        binVertices = []
        binIds = []
        nVertices = []
        for i in range(0, len(nodes)):
            verticeArray = nodes[i]
            packedVertices = b''.join(verticeArray)
            binVertices.append(packedVertices)
            nVertices.append(len(verticeArray))
            if batched:
                binIds.append(np.full(len(verticeArray), i, dtype=np.uint16))

        glTF.header = compute_header(1, binVertices, [], binIds,
                                     nVertices, bb, transform,
                                     binary, batched, uri)
        glTF.body = np.frombuffer(
            compute_binary(binVertices, [], binIds), dtype=np.uint8)

        return glTF

    @staticmethod
    def from_wkb_as_triangles(wkbs, bboxes, transform, binary=True, batched=True, uri=None, include_normals=True):
        """
        Parameters
        ----------
        wkbs : array
            Array of wkbs

        bboxes : array
            Array of bounding boxes (numpy.array)

        transform : numpy.array
            World coordinates transformation flattend matrix

        Returns
        -------
        glTF : GlTF
        """

        glTF = GlTF()
        nodes = []
        normals = []
        bb = []
        for wkb, bbox in zip(wkbs, bboxes):
            mp = parse_to_triangles(bytes(wkb))
            triangles = []
            for poly in mp:
                triangles.extend(triangulate(poly))
            nodes.append(triangles)
            if include_normals:
                normals.append(compute_normals(triangles))

            bb.append(bbox)

        binVertices = []
        binNormals = []
        binIds = []
        nVertices = []
        for i in range(0, len(nodes)):
            (verticeArray, normalArray) = trianglesToArrays(
                nodes[i],
                normals[i] if include_normals else None)
            packedVertices = b''.join(verticeArray)
            binVertices.append(packedVertices)
            if include_normals:
                binNormals.append(b''.join(normalArray))
            nVertices.append(len(verticeArray))
            if batched:
                binIds.append(np.full(len(verticeArray), i, dtype=np.uint16))

        glTF.header = compute_header(4, binVertices, binNormals, binIds,
                                     nVertices, bb, transform,
                                     binary, batched, uri)
        glTF.body = np.frombuffer(
            compute_binary(binVertices, binNormals, binIds), dtype=np.uint8)

        return glTF


def compute_binary(binVertices, binNormals, binIds):
    bv = b''.join(binVertices)
    bn = b''.join(binNormals)
    bid = b''.join(binIds)
    return bv + bn + bid


def compute_header(mode, binVertices, binNormals, binIds,
                   nVertices, bb, transform,
                   bgltf, batched, uri):
    # Buffer
    meshNb = len(binVertices)
    sizeVce = []
    for i in range(0, meshNb):
        sizeVce.append(len(binVertices[i]))

    has_normals = len(binNormals) > 0

    buffers = {
        'binary_glTF': {
            'byteLength': (6 + 6 * int(has_normals) + 1)/6 * sum(sizeVce) if batched else 2 * sum(sizeVce),
            'type': "arraybuffer"
        }
    }
    if uri is not None:
        buffers["binary_glTF"]["uri"] = uri

    # Buffer view
    bufferViews = {
        'BV_vertices': {
            'buffer': "binary_glTF",
            'byteLength': sum(sizeVce),
            'byteOffset': 0,
            'target': 34962
        },
    }
    byteOffset = bufferViews['BV_vertices']['byteLength']

    if has_normals:
        bufferViews['BV_normals'] = {
            'buffer': "binary_glTF",
            'byteLength': sum(sizeVce),
            'byteOffset': byteOffset,
            'target': 34962
        }
        byteOffset += bufferViews['BV_normals']['byteLength']

    if batched:
        bufferViews['BV_ids'] = {
            'buffer': "binary_glTF",
            'byteLength': sum(sizeVce) / 6,
            'byteOffset': byteOffset,
            'target': 34962
        }

    # Accessor
    accessors = {}
    if batched:
        accessors["AV"] = {
            'bufferView': "BV_vertices",
            'byteOffset': 0,
            'byteStride': 12,
            'componentType': 5126,
            'count': sum(nVertices),
            'max': [max([bb[i][0][1] for i in range(0, meshNb)]),
                    max([bb[i][0][2] for i in range(0, meshNb)]),
                    max([bb[i][0][0] for i in range(0, meshNb)])],
            'min': [min([bb[i][1][1] for i in range(0, meshNb)]),
                    min([bb[i][1][2] for i in range(0, meshNb)]),
                    min([bb[i][1][0] for i in range(0, meshNb)])],
            'type': "VEC3"
        }
        if has_normals:
            accessors["AN"] = {
                'bufferView': "BV_normals",
                'byteOffset': 0,
                'byteStride': 12,
                'componentType': 5126,
                'count': sum(nVertices),
                'max': [1, 1, 1],
                'min': [-1, -1, -1],
                'type': "VEC3"
            }
        accessors["AD"] = {
            'bufferView': "BV_ids",
            'byteOffset': 0,
            'byteStride': 2,
            'componentType': 5123,
            'count': sum(nVertices),
            'type': "SCALAR"
        }
    else:
        for i in range(0, meshNb):
            accessors["AV_" + str(i)] = {
                'bufferView': "BV_vertices",
                'byteOffset': sum(sizeVce[0:i]),
                'byteStride': 12,
                'componentType': 5126,
                'count': nVertices[i],
                'max': [bb[i][0][1], bb[i][0][2], bb[i][0][0]],
                'min': [bb[i][1][1], bb[i][1][2], bb[i][1][0]],
                'type': "VEC3"
            }
            if has_normals:
                accessors["AN_" + str(i)] = {
                    'bufferView': "BV_normals",
                    'byteOffset': sum(sizeVce[0:i]),
                    'byteStride': 12,
                    'componentType': 5126,
                    'count': nVertices[i],
                    'max': [1, 1, 1],
                    'min': [-1, -1, -1],
                    'type': "VEC3"
                }

    # Meshes
    meshes = {}
    if batched:
        meshes["M"] = {
            'primitives': [{
                'attributes': {
                    "POSITION": "AV",
                    "_BATCHID": "AD"
                },
                "material": "defaultMaterial",
                "mode": mode
            }]
        }

        if has_normals:
            meshes['M']['primitives'][0]['attributes']['NORMAL'] = 'AN'
    else:
        for i in range(0, meshNb):
            meshes["M" + str(i)] = {
                'primitives': [{
                    'attributes': {
                        "POSITION": "AV_" + str(i),
                        "NORMAL": "AN_" + str(i)
                    },
                    "indices": "AI_" + str(i),
                    "material": "defaultMaterial",
                    "mode": mode
                }]
            }

            if has_normals:
                meshes['M' + str(i)]['primitives']['attributes']['NORMAL'] = 'AN' + str(i)

    # Nodes
    if batched:
        nodes = {
            'node': {
                'matrix': [float(e) for e in transform],
                'meshes': ["M"]
            }
        }
    else:
        nodes = {
            'node': {
                'matrix': [float(e) for e in transform],
                'meshes': ["M" + str(i) for i in range(0, meshNb)]
            }
        }
    # TODO: one node per feature would probably be better

    # Extensions
    extensions = []
    if bgltf:
        extensions.append("KHR_binary_glTF")

    # Final glTF
    header = {
        'scene': "defaultScene",
        'scenes': {
            'defaultScene': {
                'nodes': [
                    "node"
                ]
            }
        },
        'nodes': nodes,
        'meshes': meshes,
        'accessors': accessors,
        'bufferViews': bufferViews,
        'buffers': buffers,
        'materials': {
            'defaultMaterial': {
                'name': "None"
            }
        }
    }

    # Technique for batched glTF
    """if batched:
        header['materials']['defaultMaterial']['technique'] = "T0"
        header['techniques'] = {
            "T0": {
                "attributes": {
                    "a_batchId": "batchId"
                },
                "parameters": {
                    "batchId": {
                        "semantic": "_BATCHID",
                        "type": 5123
                    }
                }
            }
        }
    """

    if len(extensions) != 0:
        header["extensionsUsed"] = extensions

    return header


def trianglesToArrays(triangles, normals):
    vertice = []
    normalArray = []
    for i in range(0, len(triangles)):
        n = normals[i]
        for vertex in triangles[i]:
            vertice.append(vertex)
            normalArray.append(n)
    return (vertice, normalArray)


def triangulate(poly):
    """
    Triangulates 3D polygons
    """
    polygon = poly[0]
    holes = poly[1:]

    holes_index = []
    allVertices = polygon[:]
    for elem in holes:
      #print(len(elem))
      holes_index += [len(allVertices)]
      allVertices.extend(elem)
    #if len(holes_index) > 0:
        #print(len(allVertices))
        #print(holes_index)
    vect1 = polygon[1] - polygon[0]
    vect2 = polygon[2] - polygon[0]
    vectProd = np.cross(vect1, vect2)
    polygon2D = []
    segments = []
    for i in range(len(polygon)):
        segments.append([i, (i+1)%len(polygon)])
    idx = len(polygon)
    for hole in holes:
      for i in range(len(hole)):
        segments.append([i + idx, (i+1)%len(hole) + idx])
      idx += len(hole)

    # triangulation of the polygon projected on planes (xy) (zx) or (yz)
    if(math.fabs(vectProd[0]) > math.fabs(vectProd[1])
       and math.fabs(vectProd[0]) > math.fabs(vectProd[2])):
        # (yz) projection
        x = 1
        y = 2
    elif(math.fabs(vectProd[1]) > math.fabs(vectProd[2])):
        # (zx) projection
        x = 0
        y = 2
    else:
        # (xy) projextion
        x = 0
        y = 1
    for v in range(0, len(polygon)):
        polygon2D.append([polygon[v][x], polygon[v][y]])
    for hole in holes:
        for v in range(0, len(hole)):
            polygon2D.append([hole[v][x], hole[v][y]])

    args = {'vertices': polygon2D}
    #        'segments': segments}
    if False and len(holes) != 0:
        holePoints = []
        for hole in holes:
            polygon = Polygon([(point[x], point[y]) for point in hole])

            idx = 0
            # find a point inside the hole
            while True:
                if idx > len(hole) - 3:
                    # as polygon are closed, this shouldn't happen
                    raise 'Cannot find a point in polygon'
                holePoint = [(hole[idx][x] + hole[idx+1][x] + hole[idx+2][x]) / 3,
                    (hole[idx+0][y] + hole[idx+1][y] + hole[idx+2][y]) / 3]
                if polygon.contains(Point(holePoint[0], holePoint[1])):
                  break
                idx+=1

            holePoints.append(holePoint)
        args['holes'] = holePoints

    ear = True

    if ear:
        vertices = [coord for vert in args['vertices'] for coord in vert]
        hole_base = len(args['vertices'])
        holes = []
        #if 'holes' in args:
        #    vertices += [coord for vert in args['holes'] for coord in vert]
        #    hole_count = len(args['holes'])
        #    holes = [hole_base + i for i in range(hole_count)]
        #    holes = []

        #print(vertices)
        #print(holes)
        trianglesIdx = earcut(vertices, holes_index, 2)
        if len(trianglesIdx) == 0:
            return []
    else:
        pass
        # triangulation = triangle.triangulate(args, 'pS0')
        # if 'triangles' not in triangulation:    # if polygon is degenerate
        #     return []
        #trianglesIdx = triangulation['triangles']
    triangles = []
    t = trianglesIdx
    #print('{} -> {}'.format(len(trianglesIdx), trianglesIdx))
    for i in range(0, len(trianglesIdx), 3):
        # triangulation may break triangle orientation, test it before
        # adding triangles
        #print('{} {} {} ({})'.format(t[i + 0], t[i + 1], t[i + 2], len(allVertices)))
        if(t[i + 0] > t[i + 1] > t[i + 2] or t[i + 2] > t[i + 0] > t[i + 1] or t[i + 1] > t[i + 2] > t[i + 0]):
            triangles.append([allVertices[t[i + 1]], allVertices[t[i + 0]], allVertices[t[i + 2]]])
        else:
            triangles.append([allVertices[t[i + 0]], allVertices[t[i + 1]], allVertices[t[i + 2]]])

    return triangles


def compute_normals(triangles):
    normals = []
    for t in triangles:
        U = t[1] - t[0]
        V = t[2] - t[0]
        N = np.cross(U, V)
        norm = np.linalg.norm(N)
        if norm == 0:
            normals.append(np.array([1, 0, 0], dtype=np.float32))
        else:
            normals.append(N / norm)
    return normals

def parse_to_lines(wkb):
    """
    Expects Multipolygon Z
    """
    multiPolygon = []
    # length = len(wkb)
    # print(length)
    # byteorder = struct.unpack('b', wkb[0:1])
    # print(byteorder)
    # geomtype = struct.unpack('I', wkb[1:5])    # 1006 (Multipolygon Z)
    # print(geomtype)
    typ = struct.unpack('I', wkb[1:5])[0]

    if typ != 1005 and typ != 1006:
        print('Unsupported geom type:' + str(typ))
        return None

    geomNb = struct.unpack('I', wkb[5:9])[0]
    # print(geomNb)
    # print(struct.unpack('b', wkb[9:10])[0])
    # print(struct.unpack('I', wkb[10:14])[0])   # 1003 (Polygon)
    # print(struct.unpack('I', wkb[14:18])[0])   # num lines
    # print(struct.unpack('I', wkb[18:22])[0])   # num points
    offset = 9
    line_segments = []
    for i in range(0, geomNb):
        offset += 5  # struct.unpack('bI', wkb[offset:offset+5])[0]
        # 1 (byteorder), 1003 (Polygon)

        if typ == 1006: # multipolygon Z
            lineNb = struct.unpack('I', wkb[offset:offset+4])[0]
            offset += 4
        elif typ == 1005: # multiline Z
            lineNb = 1
        else:
            print(wkb[1:5])
            print('foo ' + str(typ))
            raise 'rr'
        for j in range(0, lineNb):
            pointNb = struct.unpack('I', wkb[offset:offset+4])[0]  # num points
            offset += 4
            line = []
            previous_point = None
            # print(pointNb)
            for k in range(0, pointNb):
                point = np.array(struct.unpack('ddd', wkb[offset:offset+24]),
                                 dtype=np.float32)
                offset += 24
                # todo: for polygon we should draw using closed lines
                if k >= 2:
                    line_segments.append(previous_point)
                line_segments.append(point)
                previous_point = point

    return line_segments


def parse_to_triangles(wkb):
    """
    Expects Multipolygon Z
    """
    multiPolygon = []
    # length = len(wkb)
    # print(length)
    # byteorder = struct.unpack('b', wkb[0:1])
    # print(byteorder)
    # geomtype = struct.unpack('I', wkb[1:5])    # 1006 (Multipolygon Z)
    # print(geomtype)
    geomNb = struct.unpack('I', wkb[5:9])[0]
    # print(geomNb)
    # print(struct.unpack('b', wkb[9:10])[0])
    # print(struct.unpack('I', wkb[10:14])[0])   # 1003 (Polygon)
    # print(struct.unpack('I', wkb[14:18])[0])   # num lines
    # print(struct.unpack('I', wkb[18:22])[0])   # num points
    offset = 9
    for i in range(0, geomNb):
        offset += 5  # struct.unpack('bI', wkb[offset:offset+5])[0]
        # 1 (byteorder), 1003 (Polygon)
        lineNb = struct.unpack('I', wkb[offset:offset+4])[0]
        offset += 4
        polygon = []
        for j in range(0, lineNb):
            pointNb = struct.unpack('I', wkb[offset:offset+4])[0]  # num points
            offset += 4
            line = []
            for k in range(0, pointNb-1):
                point = np.array(struct.unpack('ddd', wkb[offset:offset+24]),
                                 dtype=np.float32)
                offset += 24
                line.append(point)
            offset += 24   # skip redundant point
            polygon.append(line)
        multiPolygon.append(polygon)
    return multiPolygon
