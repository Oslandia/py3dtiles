# -*- coding: utf-8 -*-
import struct
import numpy as np
import json


class GlTF(object):

    def __init__(self):
        self.header = {}
        self.body = None

    def to_array(self):  # glb
        scene = json.dumps(self.header, separators=(',', ':'))

        # body must be 4-byte aligned
        scene += ' '*((4 - len(scene) % 4) % 4)

        padding = np.array([0 for i in range(0, (4 - len(self.body) % 4) % 4)],
                           dtype=np.uint8)

        length = 28 + len(self.body) + len(scene) + len(padding)
        binaryHeader = np.array([0x46546C67,  # "glTF" magic
                                 2,  # version
                                 length], dtype=np.uint32)
        jsonChunkHeader = np.array([len(scene),  # JSON chunck length
                                    0x4E4F534A], dtype=np.uint32)  # "JSON"

        binChunkHeader = np.array([len(self.body) + len(padding),
                                   # BIN chunck length
                                   0x004E4942], dtype=np.uint32)  # "BIN"

        return np.concatenate((binaryHeader.view(np.uint8),
                               jsonChunkHeader.view(np.uint8),
                               np.fromstring(scene, dtype=np.uint8),
                               binChunkHeader.view(np.uint8),
                               self.body,
                               padding))

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
    def from_binary_arrays(arrays, transform, binary=True, batched=True,
                           uri=None):
        """
        Parameters
        ----------
        arrays : array of dictionaries
            Each dictionary has the data for one geometry
            arrays['position']: binary array of vertex positions
            arrays['normal']: binary array of vertex normals
            arrays['uv']: binary array of vertex texture coordinates
                          (Not implemented yet)
            arrays['bbox']: geometry bounding box (numpy.array)

        transform : numpy.array
            World coordinates transformation flattend matrix

        Returns
        -------
        glTF : GlTF
        """

        glTF = GlTF()

        binVertice = []
        binNormals = []
        binIds = []
        nVertice = []
        bb = []
        for i, geometry in enumerate(arrays):
            binVertice.append(geometry['position'])
            binNormals.append(geometry['normal'])
            n = round(len(geometry['position']) / 12)
            nVertice.append(n)
            bb.append(geometry['bbox'])
            if batched:
                binIds.append(np.full(n, i, dtype=np.uint32))

        glTF.header = compute_header(binVertice, binNormals, binIds,
                                     nVertice, bb, transform,
                                     binary, batched, uri)
        glTF.body = np.frombuffer(
            compute_binary(binVertice, binNormals, binIds), dtype=np.uint8)

        return glTF


def compute_binary(binVertices, binNormals, binIds):
    bv = b''.join(binVertices)
    bn = b''.join(binNormals)
    bid = b''.join(binIds)
    return bv + bn + bid


def compute_header(binVertices, binNormals, binIds,
                   nVertices, bb, transform,
                   bgltf, batched, uri):
    # Buffer
    meshNb = len(binVertices)
    sizeVce = []
    for i in range(0, meshNb):
        sizeVce.append(len(binVertices[i]))

    buffers = [{
        'byteLength': int(round(7/3 * sum(sizeVce) if batched
                          else 2 * sum(sizeVce)))
    }]
    if uri is not None:
        buffers["binary_glTF"]["uri"] = uri

    # Buffer view
    bufferViews = []
    # vertices
    bufferViews.append({
        'buffer': 0,
        'byteLength': sum(sizeVce),
        'byteOffset': 0,
        'target': 34962
    })
    bufferViews.append({
        'buffer': 0,
        'byteLength': sum(sizeVce),
        'byteOffset': sum(sizeVce),
        'target': 34962
    })
    if batched:
        bufferViews.append({
            'buffer': 0,
            'byteLength': int(round(sum(sizeVce) / 3)),
            'byteOffset': 2 * sum(sizeVce),
            'target': 34962
        })

    # Accessor
    accessors = []
    if batched:
        # Vertices
        accessors.append({
            'bufferView': 0,
            'byteOffset': 0,
            'componentType': 5126,
            'count': sum(nVertices),
            'max': [max([bb[i][0][1] for i in range(0, meshNb)]),
                    max([bb[i][0][2] for i in range(0, meshNb)]),
                    max([bb[i][0][0] for i in range(0, meshNb)])],
            'min': [min([bb[i][1][1] for i in range(0, meshNb)]),
                    min([bb[i][1][2] for i in range(0, meshNb)]),
                    min([bb[i][1][0] for i in range(0, meshNb)])],
            'type': "VEC3"
        })
        # normals
        accessors.append({
            'bufferView': 1,
            'byteOffset': 0,
            'componentType': 5126,
            'count': sum(nVertices),
            'max': [1, 1, 1],
            'min': [-1, -1, -1],
            'type': "VEC3"
        })
        # ids
        accessors.append({
            'bufferView': 2,
            'byteOffset': 0,
            'componentType': 5126,
            'count': sum(nVertices),
            'max': [meshNb],
            'min': [0],
            'type': "SCALAR"
        })
    else:
        for i in range(0, meshNb):
            # vertices
            accessors.append({
                'bufferView': 0,
                'byteOffset': sum(sizeVce[0:i]),
                'componentType': 5126,
                'count': nVertices[i],
                'max': [bb[i][0][1], bb[i][0][2], bb[i][0][0]],
                'min': [bb[i][1][1], bb[i][1][2], bb[i][1][0]],
                'type': "VEC3"
            })
            # normals
            accessors.append({
                'bufferView': 1,
                'byteOffset': sum(sizeVce[0:i]),
                'componentType': 5126,
                'count': nVertices[i],
                'max': [1, 1, 1],
                'min': [-1, -1, -1],
                'type': "VEC3"
            })

    # Meshes
    meshes = []
    if batched:
        meshes.append({
            'primitives': [{
                'attributes': {
                    "POSITION": 0,
                    "NORMAL": 1,
                    "_BATCHID": 2
                },
                "mode": 4
            }]
        })
    else:
        for i in range(0, meshNb):
            meshes.append({
                'primitives': [{
                    'attributes': {
                        "POSITION": 2 * i,
                        "NORMAL": 2 * i + 1
                    },
                    "mode": 4
                }]
            })

    # Nodes
    if batched:
        nodes = [{
                'matrix': [float(e) for e in transform],
                'mesh': 0
            }]
    else:
        nodes = []
        for i in range(0, meshNb):
            nodes.append({
                'matrix': [float(e) for e in transform],
                'mesh': i
            })

    # Final glTF
    header = {
        'asset': {
            "generator": "py3dtiles",
            "version": "2.0"
        },
        'scene': 0,
        'scenes': [{
            'nodes': [i for i in range(0, len(nodes))]
        }],
        'nodes': nodes,
        'meshes': meshes,
        'accessors': accessors,
        'bufferViews': bufferViews,
        'buffers': buffers
    }

    return header
