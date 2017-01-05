# -*- coding: utf-8 -*-
import struct
import binascii
import math
import triangle
import numpy as np

class GlTF(object):

    def __init__(self):
        self.header = {}
        self.body = None

    def to_array(self): # bgl
        return 0

    @staticmethod
    def from_array(positions_dtype, positions):
        glTF = GlTF()

        return glTF

    @staticmethod
    def from_wkb(wkbs, bboxes, transform):
        # TODO: handle transform
        """
        Parameters
        ----------
        wkbs : array
            Array of wkbs

        bboxes : array
            Array of bounding boxes (numpy.array)

        transform : numpy.array
            World coordinates transformation matrix

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
            normals.append(computeNormals(triangles))

            bb.append(bbox)

        data = ([], [], [], [])
        binVertices = []
        binIndices = []
        binNormals = []
        nVertices = []
        nIndices = []
        for i in range(0,len(nodes)):
            ptsIdx = indexation(nodes[i], normals[i])
            packedVertices = b''.join(ptsIdx[0])
            binVertices.append(packedVertices)
            binIndices.append(struct.pack('H'*len(ptsIdx[2]), *ptsIdx[2]))
            binNormals.append(b''.join(ptsIdx[1]))
            nVertices.append(len(ptsIdx[0]))
            nIndices.append(len(ptsIdx[2]))

        glTF.header = outputJSON(binVertices, binIndices, binNormals, nVertices, nIndices, bb, False, "test.bin")
        glTF.body = outputBin(binVertices, binIndices, binNormals)
        glTF.temp = outputbglTF(binVertices, binIndices, binNormals, nVertices, nIndices, bb)

        return glTF

def outputbglTF(binVertices, binIndices, binNormals, nVertices, nIndices, bb):
    scene = outputJSON(binVertices, binIndices, binNormals, nVertices, nIndices, bb, True)

    scene = struct.pack(str(len(scene)) + 's', scene.encode('utf8'))
    # body must be 4-byte aligned
    trailing = len(scene) % 4
    if trailing != 0:
        scene = scene + struct.pack(str(trailing) + 's', b' ' * trailing)

    body = outputBin(binVertices, binIndices, binNormals)

    header = struct.pack('4s', "glTF".encode('utf8')) + \
                struct.pack('I', 1) + \
                struct.pack('I', 20 + len(body) + len(scene)) + \
                struct.pack('I', len(scene)) + \
                struct.pack('I', 0)

    return header + scene + body

def outputBin(binVertices, binIndices, binNormals):
    binary = b''.join(binVertices)
    binary = binary + b''.join(binNormals)
    binary = binary + b''.join(binIndices)
    return binary

def outputJSON(binVertices, binIndices, binNormals, nVertices, nIndices, bb, bgltf, uri = "data:,"):
    # Buffer
    meshNb = len(binVertices)
    sizeIdx = []
    sizeVce = []
    for i in range(0, meshNb):
        sizeVce.append(len(binVertices[i]))
        sizeIdx.append(len(binIndices[i]))

    uriStr = uri
    if uri != "":
        uriStr = ',"uri": "{0}"'.format(uri)
    buffers = """\
"binary_glTF": {{
    "byteLength": {0},
    "type": "arraybuffer"
}}""".format(2 * sum(sizeVce) + sum(sizeIdx))

    # Buffer view
    bufferViews = """\
"BV_indices": {{
    "buffer": "binary_glTF",
    "byteLength": {0},
    "byteOffset": {2},
    "target": 34963
}},
"BV_vertices": {{
    "buffer": "binary_glTF",
    "byteLength": {1},
    "byteOffset": 0,
    "target": 34962
}},
"BV_normals": {{
    "buffer": "binary_glTF",
    "byteLength": {1},
    "byteOffset": {1},
    "target": 34962
}}""".format(sum(sizeIdx), sum(sizeVce), 2 * sum(sizeVce))

    # Accessor
    accessors = ""
    for i in range(0, meshNb):
        bbmin = str(bb[i][0][1]) + ',' + str(bb[i][0][2]) + ',' + str(bb[i][0][0])
        bbmax = str(bb[i][1][1]) + ',' + str(bb[i][1][2]) + ',' + str(bb[i][1][0])
        accessors = accessors + """\
"AI_{0}": {{
    "bufferView": "BV_indices",
    "byteOffset": {1},
    "byteStride": 2,
    "componentType": 5123,
    "count": {3},
    "type": "SCALAR"
}},
"AV_{0}": {{
    "bufferView": "BV_vertices",
    "byteOffset": {2},
    "byteStride": 12,
    "componentType": 5126,
    "count": {4},
    "max": [{5}],
    "min": [{6}],
    "type": "VEC3"
}},
"AN_{0}": {{
    "bufferView": "BV_normals",
    "byteOffset": {2},
    "byteStride": 12,
    "componentType": 5126,
    "count": {4},
    "max": [1,1,1],
    "min": [-1,-1,-1],
    "type": "VEC3"
}},""".format(i, sum(sizeIdx[0:i]), sum(sizeVce[0:i]), nIndices[i], nVertices[i], bbmax, bbmin)
    accessors = accessors[0:len(accessors)-1]

    # Meshes
    meshes = ""
    for i in range(0, meshNb):
        meshes = meshes + """\
"M{0}": {{
    "primitives": [{{
        "attributes": {{
            "POSITION": "AV_{0}",
            "NORMAL": "AN_{0}"
        }},
        "indices": "AI_{0}",
        "material": "defaultMaterial",
        "mode": 4
    }}]
}},""".format(i)

    meshes = meshes[0:len(meshes)-1]

    # Nodes
    meshesId = ""
    for i in range(0, meshNb):
        meshesId += '"M{0}",'.format(i)
    meshesId = meshesId[0:len(meshesId)-1]

    nodes = ""
    nodes = nodes + """\
"node": {{
    "meshes": [{0}]
}}""".format(meshesId)

    # Extension
    extension = ""
    if bgltf:
        extension = """,\
"extensionsUsed" : [
    "KHR_binary_glTF"
]"""

    # Final glTF
    JSON = """\
{{
    "scene": "defaultScene",
    "scenes": {{
        "defaultScene": {{
            "nodes": [
                "node"
            ]
        }}
    }},
    "nodes": {{
        {0}
    }},
    "meshes": {{
        {1}
    }},
    "accessors": {{
        {2}
    }},
    "bufferViews": {{
        {3}
    }},
    "buffers": {{
        {4}
    }},
    "materials": {{
        "defaultMaterial": {{
            "name": "None"
        }}
    }}{5}
}}""".format(nodes, meshes, accessors, bufferViews, buffers, extension)

    return JSON


def indexation(triangles, normals):
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
        n = normals[i]#struct.pack('fff', *normals[i])
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


def computeNormals(triangles):
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

# TODO: remove
import binascii
if __name__ == "__main__":
    wkb = binascii.unhexlify("01f70300000f00000001eb03000001000000050000000000240857001fc0000000f0c16b1dc000514b73bb89fe3f0000c0b4a83f1fc00000805ad3fcf7bf00514b73bb89fe3f0000c0b4a83f1fc00000805ad3fcf7bf40ba11164d6e00c00000240857001fc0000000f0c16b1dc040ba11164d6e00c00000240857001fc0000000f0c16b1dc000514b73bb89fe3f01eb030000010000000500000000003023f5be0f40000040800ced1cc000514b73bb89fe3f0000240857001fc0000000f0c16b1dc000514b73bb89fe3f0000240857001fc0000000f0c16b1dc040ba11164d6e00c000003023f5be0f40000040800ced1cc040ba11164d6e00c000003023f5be0f40000040800ced1cc000514b73bb89fe3f01eb030000010000000500000000003023f5be0f40000040800ced1cc040ba11164d6e00c00000f8c951400f400000c09bfd01f6bf40ba11164d6e00c00000f8c951400f400000c09bfd01f6bf00514b73bb89fe3f00003023f5be0f40000040800ced1cc000514b73bb89fe3f00003023f5be0f40000040800ced1cc040ba11164d6e00c001eb03000001000000050000000000d8f6769b21400000c0b12e2ef5bf40ba11164d6e00c000002477d86c2140000010527e321d4040ba11164d6e00c000002477d86c2140000010527e321d4000895fb14e6e00400000d8f6769b21400000c0b12e2ef5bf00895fb14e6e00400000d8f6769b21400000c0b12e2ef5bf40ba11164d6e00c001eb030000010000000500000000002477d86c2140000010527e321d4040ba11164d6e00c000009a5ab67e21c000006024b4751c4040ba11164d6e00c000009a5ab67e21c000006024b4751c4000895fb14e6e004000002477d86c2140000010527e321d4000895fb14e6e004000002477d86c2140000010527e321d4040ba11164d6e00c001eb030000010000000500000000005ab9175021c0000080685721f8bf00895fb14e6e004000009a5ab67e21c000006024b4751c4000895fb14e6e004000009a5ab67e21c000006024b4751c4040ba11164d6e00c000005ab9175021c0000080685721f8bf40ba11164d6e00c000005ab9175021c0000080685721f8bf00895fb14e6e004001eb03000001000000040000000000c0b4a83f1fc00000805ad3fcf7bf00895fb14e6e00400000dc09f67720c00000c0e7150ff8bf40ba11164d6e00c00000c0b4a83f1fc00000805ad3fcf7bf00514b73bb89fe3f0000c0b4a83f1fc00000805ad3fcf7bf00895fb14e6e004001eb03000001000000040000000000c0b4a83f1fc00000805ad3fcf7bf00514b73bb89fe3f0000dc09f67720c00000c0e7150ff8bf40ba11164d6e00c00000c0b4a83f1fc00000805ad3fcf7bf40ba11164d6e00c00000c0b4a83f1fc00000805ad3fcf7bf00514b73bb89fe3f01eb03000001000000040000000000dc09f67720c00000c0e7150ff8bf40ba11164d6e00c000005ab9175021c0000080685721f8bf00895fb14e6e004000005ab9175021c0000080685721f8bf40ba11164d6e00c00000dc09f67720c00000c0e7150ff8bf40ba11164d6e00c001eb03000001000000040000000000c0b4a83f1fc00000805ad3fcf7bf00895fb14e6e004000005ab9175021c0000080685721f8bf00895fb14e6e00400000dc09f67720c00000c0e7150ff8bf40ba11164d6e00c00000c0b4a83f1fc00000805ad3fcf7bf00895fb14e6e004001eb03000001000000040000000000d8f6769b21400000c0b12e2ef5bf00895fb14e6e0040000054698b6b1940000000ad1698f5bf40ba11164d6e00c00000d8f6769b21400000c0b12e2ef5bf40ba11164d6e00c00000d8f6769b21400000c0b12e2ef5bf00895fb14e6e004001eb03000001000000040000000000d8f6769b21400000c0b12e2ef5bf00895fb14e6e00400000f8c951400f400000c09bfd01f6bf00895fb14e6e0040000054698b6b1940000000ad1698f5bf40ba11164d6e00c00000d8f6769b21400000c0b12e2ef5bf00895fb14e6e004001eb0300000100000004000000000054698b6b1940000000ad1698f5bf40ba11164d6e00c00000f8c951400f400000c09bfd01f6bf00895fb14e6e00400000f8c951400f400000c09bfd01f6bf00514b73bb89fe3f000054698b6b1940000000ad1698f5bf40ba11164d6e00c001eb0300000100000004000000000054698b6b1940000000ad1698f5bf40ba11164d6e00c00000f8c951400f400000c09bfd01f6bf00514b73bb89fe3f0000f8c951400f400000c09bfd01f6bf40ba11164d6e00c0000054698b6b1940000000ad1698f5bf40ba11164d6e00c001eb03000001000000050000000000f8c951400f400000c09bfd01f6bf00895fb14e6e00400000c0b4a83f1fc00000805ad3fcf7bf00895fb14e6e00400000c0b4a83f1fc00000805ad3fcf7bf00514b73bb89fe3f0000f8c951400f400000c09bfd01f6bf00514b73bb89fe3f0000f8c951400f400000c09bfd01f6bf00895fb14e6e0040")

    box = [[-8.74748499994166, -7.35523200035095, -2.05385796777344], [8.8036420000717, 7.29930999968201, 2.05386103222656]]
    transform = np.identity(4, dtype=float) # TODO: translation : 1842015.125, 5177109.25, 247.87364196777344
    glTF = GlTF.from_wkb([wkb], [box], transform)

    f = open("test.gltf", 'w')
    f.write(glTF.header)
    f.close()
    f = open("test.bin", 'bw')
    f.write(bytes(glTF.body))
    f.close()

    f = open("test.glb", 'bw')
    f.write(bytes(glTF.temp))
    f.close()
