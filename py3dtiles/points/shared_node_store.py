import os
import time
import lzma
from .utils import name_to_filename


class SharedNodeStore:
    def __init__(self, manager, folder):
        self.lock = manager.Lock()
        self.metadata = manager.dict()
        self.data = manager.list()
        self.folder = folder
        self.stats = {
            'hit': manager.Value('i', 0),
            'miss': manager.Value('i', 0),
            'new': manager.Value('i', 0),
        }

    def preload(self, name):
        data = self.get(name, 0)
        if data is not None:
            self.put(name, data)

    def get(self, name, stat_inc = 1):
        self.lock.acquire()
        metadata = self.metadata.get(name, None)
        data = None
        if metadata is not None:
            data = self.data[metadata[1]]
            self.stats['hit'].value += stat_inc
        else:
            filename = name_to_filename(self.folder, name)
            if os.path.exists(filename):
                self.stats['miss'].value += stat_inc
                with open(filename, 'rb') as f:
                    data = f.read()
                os.remove(filename)
            else:
                self.stats['new'].value += stat_inc

        self.lock.release()
        return lzma.decompress(data) if data is not None else None

    def put(self, name, data):
        b = time.time()
        compressed_data = lzma.compress(data, preset=1)
        # for i in range(1, 8):
        #     print('[{}] : {}x ratio in {} sec [{} bytes]'.format(
        #         i,
        #         len(data)/len(compressed_data),
        #         round(time.time() - b, 3),
        #         len(data)))

        self.lock.acquire()
        metadata = self.metadata.get(name, None)
        if metadata is None:
            metadata = (time.time(), len(self.data))
            self.data.append(compressed_data)
        else:
            metadata = (time.time(), metadata[1])
            self.data[metadata[1]] = compressed_data
        self.metadata.update([(name, metadata)])
        self.lock.release()

    def remove_oldest_nodes(self, percent):
        self.lock.acquire()
        count = _remove_all(self)
        assert(len(self.metadata) == 0)
        assert(len(self.data) == 0)
        self.lock.release()
        return count


        sorted_entries = sorted([(name, metadata) for name, metadata in self.metadata.items()],
            key=lambda f: f[1][0])

        print('Time Diff = {}'.format(
            round(sorted_entries[-1][1][0] - sorted_entries[0][1][0], 3)))
        self.print_statistics()

        to_delete = sorted_entries[0:int(len(sorted_entries) * percent)]

        _remove_by_names(self, to_delete, True)

        self.lock.release()
        return len(to_delete)

    def print_statistics(self):
        print('Stats: Hits = {}, Miss = {}, New = {}'.format(
            self.stats['hit'].value,
            self.stats['miss'].value,
            self.stats['new'].value))


    def remove_nodes_in_level_range(self, level_range):
        self.lock.acquire()

        result = []
        to_delete = []

        for name, metadata in self.metadata.items():
            level = len(name)
            if level_range[0] <= level and level <= level_range[1]:
                to_delete += [(name, metadata)]
                filename = name_to_filename(self.folder, name)
                with open(filename, 'wb') as f:
                    f.write(self.data[metadata[1]])

        _remove_by_names(self, to_delete, False)

        # next step: read files from disk
        for folder, ignore, files in os.walk(self.folder):
            for base in files:
                fullname = '{}/{}'.format(folder, base)
                if base[0] != 'r':
                    continue
                name = ''.join([part for part in os.path.relpath(fullname, self.folder).split('/')])[1:]
                level = len(name)
                if level_range[0] <= level and level <= level_range[1]:
                    result += [fullname]

        self.lock.release()
        return result


def _remove_by_names(store, names, write_to_disk):
    result = []

    # remove metadatas
    for n, meta in names:
        del store.metadata[n]

    # sort the entry by lowering index
    names = sorted(names, key=lambda f: f[1][1], reverse=True)

    # delete the entries
    for name, meta in names:
        data = store.data.pop(meta[1])
        if write_to_disk:
            filename = name_to_filename(store.folder, name)
            with open(filename, 'wb') as f:
                f.write(data)
        result += [data]

    # shift the index
    for name, metadata in store.metadata.items():
        # count how many lower elements where removed
        shift = sum([meta[1] < metadata[1] for n, meta in names])
        store.metadata.update([(name, (metadata[0], metadata[1] - shift))])

    return result

def _remove_all(store):
    # delete the entries
    count = len(store.metadata)
    bytes_written = 0
    for name, meta in store.metadata.items():
        data = store.data[meta[1]]
        filename = name_to_filename(store.folder, name)
        with open(filename, 'wb') as f:
            bytes_written += f.write(data)

    store.metadata.clear()
    while len(store.data) > 0:
        del store.data[-1]

    return (count, bytes_written)
