import argparse
import os
import shutil
import sys
import time
import multiprocessing
import numpy as np
from laspy.file import File
import json
from memory_profiler import memory_usage
import tempfile
import time
import random
import math
import threading
import pickle
import gc
import py3dtiles
import logging
import lzma
import concurrent.futures
import liblas
import pyproj

from .points.transformations import rotation_matrix, angle_between_vectors, vector_product, inverse_matrix, scale_matrix, translation_matrix
from .points.utils import name_to_filename, compute_spacing
from .points.las_splitter import process_root_node
from .points.node_process import process_node
from .points.node_catalog import NodeCatalog
from .points.node import Node
from .points.shared_node_store import SharedNodeStore

# https://stackoverflow.com/a/43357954
def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

class DummyNode():
    def __init__(self, _bytes):
        if 'children' in _bytes:
            self.children = _bytes['children']
            self.grid = _bytes['grid']
        else:
            self.children = None
            self.points = _bytes['points']

def bytes_to_pnts(name, b, out_folder):
    b = DummyNode(pickle.loads(b))
    points = Node.get_points(b)
    count = int(len(points) / (3 * 4 + 3))

    if count == 0:
        return 0

    pdt = np.dtype([('X', '<f4'), ('Y', '<f4'), ('Z', '<f4')])
    cdt = np.dtype([('Red', 'u1'), ('Green', 'u1'), ('Blue', 'u1')])

    ft = py3dtiles.feature_table.FeatureTable()
    ft.header = py3dtiles.feature_table.FeatureTableHeader.from_dtype(pdt, cdt, count)
    ft.body = py3dtiles.feature_table.FeatureTableBody.from_array(ft.header, points)

    body = py3dtiles.pnts.PntsBody()
    body.feature_table = ft

    tile = py3dtiles.tile.Tile()
    tile.body = body
    tile.header = py3dtiles.pnts.PntsHeader()
    tile.header.sync(body)

    filename = name_to_filename(out_folder, name, '.pnts')
    tile.save_as(filename)

    return count

def temp_file_to_pnts(filename, out_folder):
    count = 0

    with open(filename, 'rb') as f:
        nodes = pickle.loads(lzma.decompress(f.read()))

        for name in nodes:
            count += bytes_to_pnts(name,
                nodes[name],
                out_folder)

    return count

def write_3dtiles(node_store, in_folder, out_folder, level_range, verbose):
    start = time.time()
    if verbose >= 1:
        print('>>>>>>>>>>>>>>>>>>>> write_3dtiles {}'.format(level_range))
    # dump_levels_on_disk(cache, in_folder, level_range, verbose)


    pool = concurrent.futures.ProcessPoolExecutor()
    jobs = []

    to_write = node_store.remove_nodes_in_level_range(level_range)

    middle = time.time()

    for data in to_write:
        jobs += [pool.submit(
            temp_file_to_pnts,
            data,
            out_folder)]

    if verbose >= 1:
        print('{} files to write for levels {}'.format(len(jobs), level_range))
    pool.shutdown()
    count = sum([j.result() for j in jobs])

    if verbose >= 1:
        print('<<<<<<<<<<<<<<<<<<<< write_3dtiles {} {} = {}, {} sec'.format(
            level_range, count,
            round(middle - start, 3),
            round(time.time() - middle, 3)))
    return count

def write_tileset(in_folder, out_folder, root_aabb, offset, scale, projection, rotation_matrix):
    # compute tile transform matrix
    if rotation_matrix is None:
        transform = np.identity(4)
    else:
        transform = inverse_matrix(rotation_matrix)
    transform = np.dot(transform, scale_matrix(1.0 / scale[0]))
    transform = np.dot(translation_matrix(offset), transform)

    root_tileset = Node.to_tileset('', root_aabb, compute_spacing(root_aabb), out_folder, scale)

    root_tileset['transform'] = transform.T.reshape(16).tolist()
    root_tileset['refine'] = 'ADD'

    tileset = {
        'asset': {'version' : '1.0'},
        'geometricError': np.linalg.norm(root_aabb[1] - root_aabb[0]) / scale[0],
        'root' : root_tileset
    }

    with open('{}/tileset.json'.format(out_folder), 'w') as f:
        f.write(json.dumps(tileset))

_2_elements_tuple_size = sys.getsizeof((1, 1))
def cache_entry_size(k, v):
    # 2 dict = 2 keys + the content of each dict
    return 2 * sys.getsizeof(k) + \
        sys.getsizeof(v) + sys.getsizeof(v[0]) + sys.getsizeof(v[1]) + sys.getsizeof(v[2]) + \
        _2_elements_tuple_size + v[1]



def keep_cache_size_under_control(cache, pid, working_dir, max_size_MB, verbose):
    bytes_to_mb = 1.0 / (1024 * 1024)
    max_size_MB = max(max_size_MB, 200)

    while True:
        time.sleep(1)

        if verbose >= 1:
            cache.print_statistics()

        before = memory_usage(proc=pid)[0]
        if before < max_size_MB:
            continue

        if verbose >= 2:
            print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> CACHE CLEANING [{}]'.format(before))
        dropped = cache.remove_oldest_nodes(1 - max_size_MB / before)
        if verbose >= 2:
            print('<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< CACHE CLEANING')

        if verbose >= 1:
            print('Mem used: {} MB. Dropped = {})'.format(
                memory_usage(proc=pid)[0],
                dropped))

def make_rotation_matrix(z1, z2):
    v0 = z1 / np.linalg.norm(z1)
    v1 = z2 / np.linalg.norm(z2)

    return rotation_matrix(
        angle_between_vectors(v0, v1),
        vector_product(v0, v1))

def main():
    parser = argparse.ArgumentParser(description='Foobar.')
    parser.add_argument('files', nargs='+', help='filenames to process')
    parser.add_argument('--out', dest='out', type=str, help='outfolder')
    parser.add_argument('--overwrite', dest='overwrite', help='erase out folder if existing', default=False, type=str2bool)
    parser.add_argument('--jobs', dest='jobs', help='parallel jobs', default=1, type=int)
    parser.add_argument('--fraction', dest='fraction', help='\% of the pointcloud to process', default=100, type=int)
    parser.add_argument('--verbose', dest='verbose', help='Print logs', default=1, type=int)
    parser.add_argument('--cache_size', dest='cache_size', help='Cache size in MB', default=1000, type=int)
    parser.add_argument('--srs_out', help='SRS to use as output (EPSG code)', type=str)
    parser.add_argument('--srs_in', help='Override input SRS (EPSG code)', type=str)
    parser.add_argument('--benchmark', help='Print summary at the end of the process', type=str)

    args = parser.parse_args()

    folder = args.out if args.out is not None else os.path.splitext(args.files[0])[0]

    # create folder
    if os.path.isdir(folder):
        if args.overwrite:
            shutil.rmtree(folder)
        else:
            print('Error, folder \'{}\' already exists'.format(folder))
            sys.exit(1)

    # working_dir = tempfile.TemporaryDirectory(prefix='py3dtiles')
    os.makedirs(folder)
    working_dir = folder + '/tmp'
    os.makedirs(working_dir)

    # srs stuff
    projection = None
    if args.srs_out is not None:
        p2 = pyproj.Proj(init='epsg:{}'.format(args.srs_out))
        # parse srs from file
        f = liblas.file.File(args.files[0])
        if args.srs_in is not None:
            p1 = pyproj.Proj(init='epsg:{}'.format(args.srs_in))
        elif f.header.srs.proj4:
            p1 = pyproj.Proj(f.header.srs.proj4)
        else:
            print('''
Error.
{} file doesn\'t contain srs information. Please use the --srs_in option to declare it.
                '''.format(args.files[0]))
            sys.exit(1)

        projection = [p1, p2]

    manager = multiprocessing.Manager()
    node_store = SharedNodeStore(manager, working_dir)

    # read all las files headers and determine the aabb/spacing
    aabb = None
    total_point_count = 0
    pointcloud_file_portions = []
    root_scale = np.array([0.01, 0.01, 0.01])
    avg_min = np.array([0., 0., 0.])
    for filename in args.files:
        f = File(filename, mode='r')
        avg_min += (np.array(f.header.min) / len(args.files))

        if aabb is None:
            aabb = np.array([f.header.get_min(), f.header.get_max()])
        else:
            bb = np.array([f.header.get_min(), f.header.get_max()])
            aabb[0] = np.minimum(aabb[0], bb[0])
            aabb[1] = np.maximum(aabb[1], bb[1])

        count = int(f.header.count * args.fraction / 100)
        total_point_count += count

        _1M = min(count, 1000000)
        steps = math.ceil(count / _1M)
        portions = [(i * _1M, min(count, (i + 1) * _1M)) for i in range(steps)]
        for p in portions:
            pointcloud_file_portions += [(filename, p)]

    rotation_matrix = None
    if projection:
        bl = np.array(list(pyproj.transform(
            projection[0], projection[1],
            aabb[0][0], aabb[0][1], aabb[0][2])))
        tr = np.array(list(pyproj.transform(
            projection[0], projection[1],
            aabb[1][0], aabb[1][1], aabb[1][2])))
        br = np.array(list(pyproj.transform(
            projection[0], projection[1],
            aabb[1][0], aabb[0][1], aabb[0][2])))

        avg_min = np.array(list(pyproj.transform(
            projection[0], projection[1],
            avg_min[0], avg_min[1], avg_min[2])))

        x_axis = br - bl

        bl = bl - avg_min
        tr = tr - avg_min

        if args.srs_out == '4978':
            # Transform geocentric normal => (0, 0, 1)
            # and 4978-bbox x axis => (1, 0, 0),
            # to have a bbox in local coordinates that's nicely aligned with the data
            rotation_matrix = make_rotation_matrix(avg_min, np.array([0, 0, 1]))
            rotation_matrix = np.dot(
                make_rotation_matrix(x_axis, np.array([1, 0, 0])),
                rotation_matrix)

            bl = np.dot(bl, rotation_matrix[:3,:3].T)
            tr = np.dot(tr, rotation_matrix[:3,:3].T)

        aabb[0] = np.minimum(bl, tr)
        aabb[1] = np.maximum(bl, tr)

        root_aabb = aabb
    else:
        # offset
        root_aabb = aabb - avg_min

    root_aabb = root_aabb * root_scale

    _4326 = pyproj.Proj(init='epsg:4326')

    root_spacing = compute_spacing(root_aabb)

    if args.verbose >= 1:
        print('Summary:')
        print('  - points to process: {}'.format(total_point_count))
        print('  - offset to use: {}'.format(avg_min))
        print('  - root spacing: {}'.format(root_spacing / root_scale[0]))

    startup = time.time()

    executor = concurrent.futures.ProcessPoolExecutor(max_workers=(args.jobs + 1))

    m = multiprocessing.Manager()
    queue = m.Queue()

    initial_portion_count = len(pointcloud_file_portions)
    random.shuffle(pointcloud_file_portions)
    pointcloud_file_splitting_result = []

    active_nodes = {}
    files_to_process = {}

    def add_file_to_process(name, file):
        assert file[1] > 0 and len(file[0]) > 0
        if name not in files_to_process:
            files_to_process[name] = [file]
        else:
            files_to_process[name] += [file]

    def can_queue_more_jobs(active, splitting):
        return len(active) + len(splitting) < args.jobs


    _3dtiles_job = None
    last_cache_test = 0
    processed_points = 0
    points_in_progress = 0
    previous_percent = 0
    written_until_level = -1
    points_in_pnts = 0
    active_jobs = {}

    cache_mgmt = multiprocessing.Process(target=keep_cache_size_under_control, args=(node_store, manager._process.pid, working_dir, args.cache_size, args.verbose))
    cache_mgmt.start()
    while True:
        now = time.time() - startup
        at_least_one_job_ended = False

        ###
        # Query process_node jobs completion
        ###
        ended_names = []
        completed = [(n, j) for (n, j) in active_nodes.items() if j.done()]
        for name, job in completed:
            del active_nodes[name]
            ended_names += [name]

        for job in set([job for n, job in completed]):
            if job in active_jobs:
                infos = active_jobs[job]

                if isinstance(infos[3][0], str):
                    # This job processed filenames.
                    # So we removed processed files.
                    for file in infos[3]:
                        os.remove(file)

                # Keep track of processed point count
                result = job.result(None)
                processed_points += result
                points_in_progress -= result
                del active_jobs[job]

        if completed:
            at_least_one_job_ended = True
            if args.verbose >= 2:
                print('')
                print('{} jobs finished'.format([j[0] for j in completed]))

        ###
        # queue is a shared queue where processes write to-be-processed files.
        ###
        while not queue.empty():
            n, files, count = queue.get()
            add_file_to_process(n, (files, count))

        pointcloud_file_splitting_result = [j for j in pointcloud_file_splitting_result if not j[0].done()]

        potential1 = sorted([(k, v) for k, v in files_to_process.items() if k in ended_names],
            key=lambda f: sum([v[1] for v in f[1]]))
        potential2 = sorted([(k, v) for k, v in files_to_process.items() if k not in active_nodes and k not in ended_names],
            # key=lambda f: -len(f[0]))
            key=lambda f: sum([v[1] for v in f[1]]))

        potential = potential2 + potential1
        # We delay job queueing until there's a free spot in the pool process. This way we can
        # process several files in one shot.
        while can_queue_more_jobs(active_jobs, pointcloud_file_splitting_result) and potential:
            job_list = []
            count = 0

            idx = len(potential) - 1
            while count < 50000 and potential and idx >= 0:
                name, files = potential[idx]
                if name not in active_nodes:
                    count += sum([f[1] for f in files])
                    job_list += [(name, files)]
                    del potential[idx]
                idx -= 1

            if job_list:
                # print('NEW JOB2 {} / {}'.format(name, len(files)))
                # Send task to another process
                todo = []
                for name, files in job_list:
                    todo += [(name, [f[0] for f in files])]

                job = executor.submit(
                    process_node,
                    node_store,
                    todo,
                    working_dir,
                    root_aabb,
                    root_spacing,
                    queue,
                    args.verbose)

                active_jobs[job] = (job_list, count, now, files)
                for name, files in job_list:
                    # Remember the files and the pointcount
                    active_nodes[name] = (job)
                    del files_to_process[name]
                    # Remove from to-be-processed list

        # for i in range(min(len(potential), 10)):
        #     node_store.preload(potential[-i][0])

        # print([p[0][0] for p in potential])
        # Continue processing the original file
        if can_queue_more_jobs(active_jobs, pointcloud_file_splitting_result): # and not pointcloud_file_splitting_result:
            # Keep active jobs
            if (pointcloud_file_portions and
                    points_in_progress < 60000000):
                if args.verbose >= 1:
                    print('Submit next portion {}'.format(pointcloud_file_portions[-1]))
                file, portion = pointcloud_file_portions.pop()
                points_in_progress += portion[1] - portion[0]
                pointcloud_file_splitting_result += [(executor.submit(
                    process_root_node,
                    working_dir,
                    file,
                    root_aabb,
                    root_spacing,
                    (-avg_min, root_scale, rotation_matrix[:3,:3].T if rotation_matrix is not None else None),
                    portion,
                    queue,
                    projection,
                    args.verbose), now)]

        if (not pointcloud_file_splitting_result and
            not pointcloud_file_portions and
            (_3dtiles_job is None or _3dtiles_job.done())):
            # we can start writing points
            level_a = min([len(i) for i in active_nodes.keys()]) if active_nodes else 10000
            level_b = min([len(i) for i in files_to_process.keys()]) if files_to_process else 10000
            writeable = min(level_a, level_b) - 1
            if writeable != written_until_level:
                if _3dtiles_job is not None:
                    points_in_pnts += _3dtiles_job.result()

                _3dtiles_job = executor.submit(
                    write_3dtiles,
                    node_store,
                    working_dir,
                    folder,
                    [written_until_level + 1, writeable],
                    args.verbose)
                written_until_level = writeable

            # Are we done yet?
            if (not active_nodes and
                not files_to_process and
                not potential and
                (_3dtiles_job is None or _3dtiles_job.done()) and
                written_until_level == 9999 and
                queue.empty()):
                    if _3dtiles_job is not None:
                        points_in_pnts += _3dtiles_job.result()
                    if args.verbose >= 1:
                        print('WAIT executor...{}'.format(points_in_pnts))
                    executor.shutdown()
                    if args.verbose >= 1:
                        print('Writing 3dtiles {}'.format(avg_min))
                    p = multiprocessing.Process(
                        target=write_tileset,
                        args=(working_dir, folder, root_aabb, avg_min, root_scale, projection, rotation_matrix))
                    p.start()
                    p.join()
                    shutil.rmtree(working_dir)
                    if args.verbose >= 1:
                        print('Done')
                    cache_mgmt.terminate()

                    if args.benchmark is not None:
                        print('{},{},{},{}'.format(
                            args.benchmark,
                            ','.join([os.path.basename(f) for f in args.files]),
                            points_in_pnts,
                            round(time.time() - startup, 1)))
                    break

        if at_least_one_job_ended:
            if args.verbose >= 2:
                print('{:^16}|{:^8}|{:^8}'.format('Name', 'Points', 'Seconds'))
                for j in pointcloud_file_splitting_result:
                    print('{:^16}|{:^8}|{:^8}'.format(
                        'root',
                        _1M,
                        round(now - j[1], 1)))

                for job, v in active_jobs.items():
                    tasks = v[0]
                    if len(tasks) == 1:
                        name = tasks[0][0]
                    else:
                        name = '{} [+{}]'.format(tasks[0][0], len(tasks) - 1)

                    print('{:^16}|{:^8}|{:^8}'.format(
                        name,
                        v[1],
                        round(now - v[2], 1)))
                print('')
                print('Pending:')
                print('  - root: {} / {}'.format(
                    len(pointcloud_file_portions),
                    initial_portion_count))
                print('  - other: {} files for {} nodes'.format(
                    sum([len(f[0]) for f in files_to_process.values()]),
                    len(files_to_process)))
                print('')

            if args.verbose >= 1:
                print('{} % points processed in {} sec [{} tasks, {} nodes]'.format(
                    round(100 * processed_points / total_point_count, 2),
                    round(now, 1),
                    len(active_jobs),
                    len(active_nodes)))
                # print(files_to_process.items())
                pending_size = sys.getsizeof(files_to_process) + \
                    sum([sys.getsizeof(k) + sys.getsizeof(v) + sum([sys.getsizeof(s[0]) for s in v]) for k, v in files_to_process.items()])
                print('Memory: {}|| [pending = {} MB, {} elements]'.format(
                    memory_usage(proc=os.getpid())[0],
                    round(pending_size / (1024 * 1024), 1),
                    sum([len(f[0]) for f in files_to_process.values()])))
                print('In progress {}'.format(points_in_progress))
            time.sleep(0.01)
        else:
            if args.verbose >= 1:
                print('.', end='', flush=True)
            else:
                if args.verbose >= 0:
                    percent = round(100 * processed_points / total_point_count, 2)
                    time_left = (100 - percent) * now / (percent + 0.001)
                    print('\r{:>6} % in {} sec [est. time left: {} sec]'.format(percent, round(now), round(time_left)), end='', flush=True)
                    if False and int(percent) != previous_percent:
                        print('')
                        previous_percent = int(percent)

            time.sleep(0.1)


if __name__ == '__main__':
    main()

