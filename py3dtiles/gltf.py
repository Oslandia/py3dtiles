# -*- coding: utf-8 -*-
import struct
import binascii
import math
import triangle
import numpy as np
import json

class GlTF(object):

    def __init__(self):
        self.header = {}
        self.body = None

    def to_array(self): # bgl
        scene = json.dumps(self.header, separators=(',', ':'))

        #scene = struct.pack(str(len(scene)) + 's', scene.encode('utf8'))
        # body must be 4-byte aligned
        scene += ' '*(4 - len(scene) % 4)

        binaryHeader = np.fromstring("glTF", dtype=np.uint8)
        binaryHeader2 = np.array([1,
                                  20 + len(self.body) + len(scene),
                                  len(scene),
                                  0], dtype=np.uint32)

        return np.concatenate((binaryHeader, binaryHeader2.view(np.uint8), np.fromstring(scene, dtype=np.uint8), np.frombuffer(self.body, dtype=np.uint8)))

    @staticmethod
    def from_wkb(wkbs, bboxes, transform, binary = True, batched = True, uri = None):
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
            mp = parse(bytes(wkb))
            triangles = []
            for poly in mp:
                if(len(poly) != 1):
                    print("No support for inner polygon rings")
                else:
                    if(len(poly[0]) > 3):
                        triangles.extend(triangulate(poly[0]))
                    else:
                        triangles.append(poly[0])
            nodes.append(triangles)
            normals.append(compute_normals(triangles))

            bb.append(bbox)

        data = ([], [], [], [])
        binVertices = []
        binIndices = []
        binNormals = []
        binIds = []
        nVertices = []
        nIndices = []
        for i in range(0,len(nodes)):
            ptsIdx = index(nodes[i], normals[i])
            packedVertices = b''.join(ptsIdx[0])
            binVertices.append(packedVertices)
            binIndices.append(struct.pack('H'*len(ptsIdx[2]), *ptsIdx[2]))
            binNormals.append(b''.join(ptsIdx[1]))
            nVertices.append(len(ptsIdx[0]))
            nIndices.append(len(ptsIdx[2]))
            if batched:
                binIds.append(np.full(len(ptsIdx[0]), i, dtype=np.uint16))

        glTF.header = compute_header(binVertices, binIndices, binNormals, binIds, nVertices, nIndices, bb, transform, binary, batched, uri)
        glTF.body = compute_binary(binVertices, binIndices, binNormals, binIds)

        return glTF

def compute_binary(binVertices, binIndices, binNormals, binIds):
    bv = b''.join(binVertices)
    bi = b''.join(binIndices)
    bn = b''.join(binNormals)
    bid = b''.join(binIds)
    return bv + bn + bi + bid

def compute_header(binVertices, binIndices, binNormals, binIds, nVertices, nIndices, bb, transform, bgltf, batched, uri):
    # Buffer
    meshNb = len(binVertices)
    sizeIdx = []
    sizeVce = []
    for i in range(0, meshNb):
        sizeVce.append(len(binVertices[i]))
        sizeIdx.append(len(binIndices[i]))

    buffers = {
        'binary_glTF': {
            'byteLength': 2 * sum(sizeVce) + sum(sizeIdx),
            'type': "arraybuffer"
        }
    }
    if uri != None:
        buffers["binary_glTF"]["uri"] = uri

    # Buffer view
    bufferViews = {
        'BV_vertices': {
            'buffer': "binary_glTF",
            'byteLength': sum(sizeVce),
            'byteOffset': 0,
            'target': 34962
        },
        'BV_normals': {
            'buffer': "binary_glTF",
            'byteLength': sum(sizeVce),
            'byteOffset': sum(sizeVce),
            'target': 34962
        },
        'BV_indices': {
            'buffer': "binary_glTF",
            'byteLength': sum(sizeIdx),
            'byteOffset': 2 * sum(sizeVce),
            'target': 34963
        }
    }
    if batched:
        bufferViews['BV_ids'] = {
            'buffer': "binary_glTF",
            'byteLength': sum(sizeVce) / 6,
            'byteOffset': sum(sizeVce) + sum(sizeIdx),
            'target': 34962
        }

    # Accessor
    accessors = {}
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
        accessors["AN_" + str(i)] = {
            'bufferView': "BV_normals",
            'byteOffset': sum(sizeVce[0:i]),
            'byteStride': 12,
            'componentType': 5126,
            'count': nVertices[i],
            'max': [1,1,1],
            'min': [-1,-1,-1],
            'type': "VEC3"
        }
        accessors["AI_" + str(i)] = {
            'bufferView': "BV_indices",
            'byteOffset': sum(sizeIdx[0:i]),
            'byteStride': 2,
            'componentType': 5123,
            'count': nIndices[i],
            'type': "SCALAR"
        }
        if batched:
            accessors["AD_" + str(i)] = {
                'bufferView': "BV_ids",
                'byteOffset': sum(sizeVce[0:i]) / 6,
                'byteStride': 2,
                'componentType': 5123,
                'count': nVertices[i],
                'type': "SCALAR"
            }

    # Meshes
    meshes = {}
    for i in range(0, meshNb):
        meshes["M" + str(i)] = {
            'primitives': [{
                'attributes': {
                    "POSITION": "AV_" + str(i),
                    "NORMAL": "AN_" + str(i)
                },
                "indices": "AI_" + str(i),
                "material": "defaultMaterial",
                "mode": 4
            }]
        }
        if batched:
            meshes["M" + str(i)]['primitives'][0]['attributes']['BATCHID'] = "AD_" + str(i)

    # Nodes
    nodes = {
        'node': {
            'matrix': [float(e) for e in transform],
            'meshes': ["M" + str(i) for i in range(0,meshNb)]
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


def index(triangles, normals):
    """
    Creates an index for points
    Replaces points in triangles by their index
    """
    index = {}
    indices = []
    orderedPoints = []
    orderedNormals = []
    maxIdx = 0

    for i in range(0, len(triangles)):
        n = normals[i]
        for pt in triangles[i]:
            if (n.tostring(),pt.tostring()) in index:
                indices.append(index[(n.tostring(),pt.tostring())])
            else:
                orderedPoints.append(pt)
                orderedNormals.append(n)
                index[(n.tostring(),pt.tostring())] = maxIdx
                indices.append(maxIdx)
                maxIdx+=1

    return (orderedPoints, orderedNormals, indices)


def triangulate(polygon):
    """
    Triangulates 3D polygons
    """
    vect1 = polygon[1] - polygon[0]
    vect2 = polygon[2] - polygon[0]
    vectProd = np.cross(vect1, vect2)
    polygon2D = []
    segments = list(range(len(polygon)))
    segments.append(0)
    # triangulation of the polygon projected on planes (xy) (zx) or (yz)
    if(math.fabs(vectProd[0]) > math.fabs(vectProd[1]) and math.fabs(vectProd[0]) > math.fabs(vectProd[2])):
        # (yz) projection
        for v in range(0,len(polygon)):
            polygon2D.append([polygon[v][1], polygon[v][2]])
    elif(math.fabs(vectProd[1]) > math.fabs(vectProd[2])):
        # (zx) projection
        for v in range(0,len(polygon)):
            polygon2D.append([polygon[v][0], polygon[v][2]])
    else:
        # (xy) projextion
        for v in range(0,len(polygon)):
            polygon2D.append([polygon[v][0], polygon[v][1]])

    triangulation = triangle.triangulate({'vertices': polygon2D, 'segments': segments})
    if 'triangles' not in triangulation:    # if polygon is degenerate
        return []
    trianglesIdx = triangulation['triangles']
    triangles = []

    for t in trianglesIdx:
        # triangulation may break triangle orientation, test it before adding triangles
        if(t[0] > t[1] > t[2] or t[2] > t[0] > t[1] or t[1] > t[2] > t[0]):
            triangles.append([polygon[t[1]], polygon[t[0]],polygon[t[2]]])
        else:
            triangles.append([polygon[t[0]], polygon[t[1]],polygon[t[2]]])

    return triangles


def compute_normals(triangles):
    normals = []
    for t in triangles:
        U = t[1] - t[0]
        V = t[2] - t[0]
        N = np.cross(U,V)
        norm = np.linalg.norm(N)
        if norm == 0:
            normals.append(np.array([1,0,0], dtype=np.float32))
        else:
            normals.append(N / norm)
    return normals


def parse(wkb):
    """
    Expects Multipolygon Z
    """
    multiPolygon = []
    #length = len(wkb)
    #print(length)
    #byteorder = struct.unpack('b', wkb[0:1])
    #print(byteorder)
    #geomtype = struct.unpack('I', wkb[1:5])    # 1006 (Multipolygon Z)
    #print(geomtype)
    geomNb = struct.unpack('I', wkb[5:9])[0]
    #print(geomNb)
    #print(struct.unpack('b', wkb[9:10])[0])
    #print(struct.unpack('I', wkb[10:14])[0])   # 1003 (Polygon)
    #print(struct.unpack('I', wkb[14:18])[0])   # num lines
    #print(struct.unpack('I', wkb[18:22])[0])   # num points
    offset = 9
    for i in range(0, geomNb):
        offset += 5#struct.unpack('bI', wkb[offset:offset+5])[0]  # 1 (byteorder), 1003 (Polygon)
        lineNb = struct.unpack('I', wkb[offset:offset+4])[0]
        offset += 4
        polygon = []
        for j in range(0, lineNb):
            pointNb = struct.unpack('I', wkb[offset:offset+4])[0]  # num points
            offset += 4
            line = []
            for k in range(0, pointNb-1):
                point = np.array(struct.unpack('ddd', wkb[offset:offset+24]), dtype=np.float32)
                offset += 24
                line.append(point)
            offset += 24   # skip redundant point
            polygon.append(line)
        multiPolygon.append(polygon);
    return multiPolygon;
