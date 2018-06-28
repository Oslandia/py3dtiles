import os
import math
import time
import pickle
import lzma

from .utils import name_to_filename, split_aabb
from .node import Node

class NodeCatalog:
    """docstring for NodeCatalog"""
    def __init__(self, node_store, folder, root_aabb, root_spacing, auto_init):
        super(NodeCatalog, self).__init__()
        self.node_store = node_store
        self.nodes = {}
        self.folder = folder
        self.root_aabb = root_aabb
        self.root_spacing = root_spacing
        self.auto_init = auto_init
        self.node_bytes = {}

    def init(self, name):
        assert len(self.nodes) == 0
        self.load_from_disk(name, True)

    def get(self, name):
        if name not in self.nodes:
            spacing = self.root_spacing / math.pow(2, len(name))
            aabb = self.root_aabb
            for i in name:
                aabb = split_aabb(aabb, int(i))
            node = Node(name, aabb, spacing)
            self.nodes[name] = node
        else:
            node = self.nodes[name]
        return node

    def _save_on_disk(self, name, recursive = True, depth = 0, max_depth = 1000000):
        node = self.nodes[name]
        if node.dirty:
            self.node_bytes[name] = node.save_to_bytes()

        if recursive and node.children is not None and depth < max_depth:
            for n in node.children:
                self._save_on_disk(n, recursive, depth + 1, max_depth)

    def save_on_disk(self, name, recursive = True, depth = 0, max_depth = 1000000):
        node = self.nodes[name]
        if node.dirty:
            self.node_bytes[name] = node.save_to_bytes()

        if recursive and node.children is not None and depth < max_depth:
            for n in node.children:
                self._save_on_disk(n, recursive, depth + 1, max_depth)

        data = pickle.dumps(self.node_bytes)
        self.node_store.put(name, data)

    def load_from_disk(self, name, allow_init):
        data = self.node_store.get(name)

        if data is not None:
            out = pickle.loads(data)
            for n in out:
                spacing = self.root_spacing / math.pow(2, len(n))
                aabb = self.root_aabb
                for i in n:
                    aabb = split_aabb(aabb, int(i))
                node = Node(n, aabb, spacing)
                node.load_from_bytes(out[n])
                self.node_bytes[n] = out[n]
                self.nodes[n] = node
        elif allow_init:
            spacing = self.root_spacing / math.pow(2, len(name))
            aabb = self.root_aabb
            for i in name:
                aabb = split_aabb(aabb, int(i))
            node = Node(name, aabb, spacing)
            self.nodes[name] = node



        return self.nodes[name]
