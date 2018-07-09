import numpy as np
import os
import time
import traceback
import pickle
from memory_profiler import memory_usage
import concurrent.futures

from .distance_test import xyz_to_child_index
from .node_catalog import NodeCatalog
from .utils import SubdivisionType, aabb_size_to_subdivision_type


def flush(node, node_catalog, max_depth=1, depth=0):
    if depth == max_depth:
        return

    # Do we have any points to push down to our children
    if len(node.pending_xyz) > 0:
        t = aabb_size_to_subdivision_type(node.aabb_size)
        for i in range(0, len(node.pending_xyz)):
            indices = xyz_to_child_index(node.pending_xyz[i], node.aabb_center)
            if t == SubdivisionType.QUADTREE:
                # map upper z to lower z
                indices = [u & 0xfe for u in indices]
                # print('NODE "{}" is quadtree'.format(node.name))
            uniques = np.unique(indices)

            # make sure all children nodes exist
            for unique_key in uniques:
                name = '{}{}'.format(node.name, unique_key)

                if name not in node.children:
                    # only store hashes
                    node.children += [name]
                    node.dirty = True

                # group by indices
                points_index = np.argwhere(indices - unique_key == 0)

                if points_index.size > 0 and len(node.pending_xyz[i]) > 0:
                    points_index = points_index.reshape(points_index.size)
                    xyz = np.take(node.pending_xyz[i], points_index, axis=0)
                    rgb = np.take(node.pending_rgb[i], points_index, axis=0)

                    node_catalog.get(name).insert(node_catalog, xyz, rgb)

        node.pending_xyz = []
        node.pending_rgb = []

    if node.children is not None:
        # then flush children
        children = node.children
        # release node
        del node
        for name in children:
            flush(node_catalog.get(name), node_catalog, max_depth, depth + 1)


def forward_unassigned_points(node_catalog, name, halt_at_depth, queue, begin, log_file):
    total = 0

    result = node_catalog.get(name).pending_to_bytes(node_catalog, halt_at_depth - 1)

    for r in result:
        if len(r) > 0:
            if log_file is not None:
                print('    -> put on queue ({},{})  [{}]'.format(r[0], r[2], time.time() - begin), file=log_file)
            total += r[2]
            queue.put(r)

    return total


def _process(node_store, folder, octree_metadata, name, filenames, queue, begin, log_file):
    node_catalog = NodeCatalog(node_store, folder, octree_metadata, True)
    node_catalog.init(name)

    log_enabled = log_file is not None

    if log_enabled:
        print('[>] process_node: "{}", {}. Mem: {}'.format(
            name, len(filenames), memory_usage(proc=os.getpid())[0]), file=log_file, flush=True)

    node = node_catalog.get(name)

    halt_at_depth = 1
    if len(name) >= 7:
        halt_at_depth = 5
    elif len(name) >= 5:
        halt_at_depth = 3
    elif len(name) > 1:
        halt_at_depth = 2

    batch = 0
    total = 0
    total_queued = 0

    for filename in filenames:
        # TODO node_catalog.keep_memory_usage_below(cache_size)
        if log_enabled:
            print('  -> read source [{}]'.format(time.time() - begin), file=log_file, flush=True)
        if isinstance(filename, str):
            with open(filename, 'rb') as f:
                raw_data = f.read()
        else:
            raw_data = filename

        data = pickle.loads(raw_data)

        point_count = len(data['xyz'])

        if log_enabled:
            print('  -> insert {} [{} points]/ {} files [{}]'.format(
                filenames.index(filename) + 1, point_count,
                len(filenames), time.time() - begin), file=log_file, flush=True)

        # insert points in node (no children handling here)
        node.insert(node_catalog, data['xyz'], data['rgb'])

        batch += point_count
        total += point_count

        if log_enabled:
            print('  -> flush [{}]'.format(time.time() - begin), file=log_file, flush=True)
        # flush push pending points (= call insert) from level N to level N + 1
        # (flush is recursive)
        flush(node, node_catalog, halt_at_depth - 1)

        # if log_enabled:
        #     print('  -> assert conditions = {} or {}'.format(halt_at_depth == 1, len(node.pending_xyz) == 0), file=log_file)
        # # at this point we only have nodes that are:
        # #  - serializable
        # #  - don't have any pending points if level < halt_at_depth - 1
        # assert halt_at_depth == 1 or len(node.pending_xyz) == 0

        if batch > 200000:
            # print('batch {}'.format(name))
            written = forward_unassigned_points(node_catalog, name, halt_at_depth, queue, begin, log_file)
            total -= written
            total_queued += written
            batch = 0

    written = forward_unassigned_points(node_catalog, name, halt_at_depth, queue, begin, log_file)
    total -= written
    total_queued += written

    if log_enabled:
        print('save on disk {} [{}]'.format(name, time.time() - begin), file=log_file)

    # save node state on disk
    node_catalog.save_on_disk(name, True, 0, halt_at_depth - 1)

    if log_enabled:
        print('saved on disk [{}]'.format(time.time() - begin), file=log_file)

    return (total, total_queued)


def process_node(node_store, work, folder, octree_metadata, queue, verbose):
    try:
        # print(">> CAS 2: {}".format(memory_usage(proc=os.getpid())))
        begin = time.time()
        log_enabled = verbose >= 2
        if log_enabled:
            log_filename = 'pytree-pid-{}.log'.format(os.getpid())
            log_file = open(log_filename, 'a')
        else:
            log_file = None

        total_queued = 0
        total = 0

        # use threads as a workaround to GIL
        if len(work) > 1:
            pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
            jobs = []
            for name, filenames in work:
                jobs += [pool.submit(_process,
                    node_store, folder, octree_metadata, name, filenames, queue, begin, log_file)]

            pool.shutdown()

            for job in jobs:
                result = job.result()
                total += result[0]
                total_queued += result[1]
        else:
            for name, filenames in work:
                result = _process(node_store, folder, octree_metadata, name, filenames, queue, begin, log_file)
                total += result[0]
                total_queued += result[1]

        if log_enabled:
            print('[<] return result [{} sec, {} MB] [{}]'.format(
                round(time.time() - begin, 2),
                memory_usage(proc=os.getpid()),
                time.time() - begin), file=log_file, flush=True)
            if log_file is not None:
                log_file.close()

        return total

    except Exception as e:
        if log_enabled or True:
            print('OH NO. {}'.format(name))
        if log_enabled or True:
            print(e)
        if log_enabled or True:
            traceback.print_exc()

    return 0
