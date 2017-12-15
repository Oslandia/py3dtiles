import numpy as np
import math
import struct
import triangle


class TriangleSoup:
    def __init__(self):
        self.triangles = []

    @staticmethod
    def from_wkb_multipolygon(wkb, associatedData=[]):
        """
        Parameters
        ----------
        wkb : string
            Well-Known Binary binary string describing a multipolygon

        associatedData : array
            array of multipolygons containing data attached to the wkb
            parameter multipolygon. Must be the same size as wkb.

        Returns
        -------
        ts : TriangleSoup
        """
        multipolygons = [parse(bytes(wkb))]

        for additionalWkb in associatedData:
            multipolygons.append(parse(bytes(additionalWkb)))

        trianglesArray = [[] for _ in range(len(multipolygons))]
        for i in range(0, len(multipolygons[0])):
            polygon = multipolygons[0][i]
            additionalPolygons = [mp[i] for mp in multipolygons[1:]]
            if(len(polygon) != 1):
                print("No support for inner polygon rings")
            else:
                if(len(polygon[0]) > 3):
                    triangles = triangulate(polygon[0],
                                            [p[0] for p in additionalPolygons])
                    for array, tri in zip(trianglesArray, triangles):
                        array += tri
                else:
                    for array, tri in zip(trianglesArray,
                                          [polygon] + additionalPolygons):
                        array += tri

        ts = TriangleSoup()
        ts.triangles = trianglesArray

        return ts

    def getPositionArray(self):
        """
        Parameters
        ----------

        Returns
        -------
        Binary array of vertice positions
        """

        verticeTriangles = self.triangles[0]
        verticeArray = vertexAttributeToArray(verticeTriangles)
        return b''.join(verticeArray)

    def getDataArray(self, index):
        """
        Parameters
        ----------
        index: int
            The index of the associated data

        Returns
        -------
        Binary array of vertice data
        """

        verticeTriangles = self.triangles[1 + index]
        verticeArray = vertexAttributeToArray(verticeTriangles)
        return b''.join(verticeArray)

    def getNormalArray(self):
        """
        Parameters
        ----------

        Returns
        -------
        Binary array of vertice normals
        """
        normals = []
        for t in self.triangles[0]:
            U = t[1] - t[0]
            V = t[2] - t[0]
            N = np.cross(U, V)
            norm = np.linalg.norm(N)
            if norm == 0:
                normals.append(np.array([0, 0, 1], dtype=np.float32))
            else:
                normals.append(N / norm)

        verticeArray = faceAttributeToArray(normals)
        return b''.join(verticeArray)


def faceAttributeToArray(triangles):
    array = []
    for face in triangles:
        array += [face, face, face]
    return array


def vertexAttributeToArray(triangles):
    array = []
    for face in triangles:
        for vertex in face:
            array.append(vertex)
    return array


def parse(wkb):
    multipolygon = []
    # length = len(wkb)
    # print(length)
    # byteorder = struct.unpack('b', wkb[0:1])
    # print(byteorder)
    geomtype = struct.unpack('I', wkb[1:5])[0]
    hasZ = (geomtype == 1006) or (geomtype == 1015)
    # MultipolygonZ or polyhedralSurface
    pntOffset = 24 if hasZ else 16
    pntUnpack = 'ddd' if hasZ else 'dd'
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
                point = np.array(struct.unpack(pntUnpack, wkb[offset:offset +
                                 pntOffset]), dtype=np.float32)
                offset += pntOffset
                line.append(point)
            offset += pntOffset   # skip redundant point
            polygon.append(line)
        multipolygon.append(polygon)
    return multipolygon


def triangulate(polygon, additionalPolygons=[]):
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
    if(math.fabs(vectProd[0]) > math.fabs(vectProd[1])
       and math.fabs(vectProd[0]) > math.fabs(vectProd[2])):
        # (yz) projection
        for v in range(0, len(polygon)):
            polygon2D.append([polygon[v][1], polygon[v][2]])
    elif(math.fabs(vectProd[1]) > math.fabs(vectProd[2])):
        # (zx) projection
        for v in range(0, len(polygon)):
            polygon2D.append([polygon[v][0], polygon[v][2]])
    else:
        # (xy) projextion
        for v in range(0, len(polygon)):
            polygon2D.append([polygon[v][0], polygon[v][1]])

    triangulation = triangle.triangulate({'vertices': polygon2D,
                                          'segments': segments})
    if 'triangles' not in triangulation:    # if polygon is degenerate
        return []
    trianglesIdx = triangulation['triangles']

    arrays = [[] for _ in range(len(additionalPolygons) + 1)]
    for t in trianglesIdx:
        # triangulation may break triangle orientation, test it before
        # adding triangles
        if(t[0] > t[1] > t[2] or t[2] > t[0] > t[1] or t[1] > t[2] > t[0]):
            for array, p in zip(arrays, [polygon] + additionalPolygons):
                array.append([p[t[1]], p[t[0]], p[t[2]]])
        else:
            for array, p in zip(arrays, [polygon] + additionalPolygons):
                array.append([p[t[0]], p[t[1]], p[t[2]]])

    return arrays
