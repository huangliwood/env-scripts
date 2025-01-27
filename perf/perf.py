#! /usr/bin/env python3

import argparse
import csv
import os
import random
import re
from multiprocessing import Process, Queue
import pandas as pd
from tqdm import tqdm
import json
from colorama import Fore, init
init(autoreset=True)
from perf_config import get_all_manip

class PerfCounters(object):
    perf_re = re.compile(r'.*\[PERF \]\[time=\s+\d+\] (([a-zA-Z0-9_]+\.)+[a-zA-Z0-9_]+): ((\w| |\')+),\s+(\d+)$')
    path_re = re.compile(r'(?P<spec_name>\w+((_\w+)|(_\w+\.\w+)|-\d+|))_(?P<time_point>\d+)_(?P<weight>0\.\d+)')

    def __init__(self, args):
        self.filename = None
        self.flag_id = "unkown"
        self.raw_counters = dict()
        self.dump_counters = dict()
        if isinstance(args, str):
            self.file_init(args)
        else:
            (falg_id,spec_dir, spec_name, spec_json) = args
            self.spec_init(falg_id, spec_dir, spec_name, spec_json)

    def file_init(self, filename: str):
        all_perf_counters = dict()
        with open(filename) as f:
            for line in f:
                perf_match = self.perf_re.match(line.replace("/", "_"))
                if perf_match:
                    perf_name = ".".join([str(perf_match.group(1)), str(perf_match.group(3))])
                    perf_value = str(perf_match.group(5))
                    perf_name = perf_name.replace(" ", "_").replace("'", "")
                    all_perf_counters[perf_name] = perf_value
        prefix_length = len(os.path.commonprefix(list(all_perf_counters.keys())))
        updated_perf = dict()
        for key in all_perf_counters:
            updated_perf[key[prefix_length:]] = all_perf_counters[key]
        self.raw_counters = updated_perf
        self.filename = filename

    def spec_init(self,flag_id: str, spec_dir: str, spec_name: str, spec_json):
        """init PerfCounters in SPEC result directory

        Args:
            spec_dir (str): SPEC result parent directory
            spec_name (str): spec_name that you need
        """
        all_perf_counters = dict()
        total_weight = 0
        for point in spec_json[spec_name]:
            weight = spec_json[spec_name][point]
            dir_name = "_".join([spec_name, point, weight])
            abs_dir = os.path.join(spec_dir, dir_name)
            if not os.path.exists(abs_dir):
                print(f"{abs_dir}路径不存在")
                return
        ### 如果没有指定Json，只有spec_name，则按照这种方式处理
        # for sub_dir in os.listdir(spec_dir):
        #     re_match = self.path_re.match(sub_dir)
        #     test_name = re_match.group("spec_name")
        #     weight = re_match.group("weight")
        #     if test_name != spec_name:
        #         continue
        #     abs_dir = os.path.join(spec_dir, sub_dir)
            tmp_counters = dict()
            # check
            check_file = os.path.join(abs_dir, "simulator_out.txt")
            flag = False
            with open(check_file) as f:
                for line in f:
                    if "EXCEEDING CYCLE/INSTR LIMIT" in line or "GOOD TRAP" in line:
                        flag = True
            if not flag:
                print(os.path.join(abs_dir),"spec 测试失败，请查看结果")
            filename = os.path.join(abs_dir, "simulator_err.txt")
            with open(filename) as f:
                for line in f:
                    perf_match = self.perf_re.match(line.replace("/", "_"))
                    if perf_match:
                        perf_name = ".".join([str(perf_match.group(1)), str(perf_match.group(3))])
                        perf_value = str(perf_match.group(5))
                        perf_name = perf_name.replace(" ", "_").replace("'", "")
                        ### warmup result will be overwritten
                        tmp_counters[perf_name] = perf_value
            ### get the weight accumulation
            for perf_name in tmp_counters:
                all_perf_counters[perf_name] = all_perf_counters.get(perf_name,0) + float(tmp_counters[perf_name]) * float(weight)
            total_weight += float(weight)

        ### do noramlization
        if total_weight == 0:
            print(f"{spec_name} does not exists in {spec_dir}")
            exit()
        for perf_name in tmp_counters:
            all_perf_counters[perf_name] = all_perf_counters[perf_name] / float(total_weight)

        prefix_length = len(os.path.commonprefix(list(all_perf_counters.keys())))
        updated_perf = dict()
        for key in all_perf_counters:
            updated_perf[key[prefix_length:]] = all_perf_counters[key]
        self.raw_counters = updated_perf
        self.filename = spec_name
        self.flag_id =flag_id

    def add_manip(self, all_manip):
        if len(self.raw_counters) == 0:
            return
        
        for manip in all_manip:
            caputure_counters=dict()
            for name in manip.counters:
                caputure_counters[name]=0
                for k in self.keys():
                    if k.endswith(name):
                        match_key = k
                        caputure_counters[name] += int(self.raw_counters[match_key])
                        print(f"merging value {match_key} -> {name} : {caputure_counters[name]}")

            numbers = map(lambda name: int(self[name]), caputure_counters)
            # self.raw_counters[manip.name] = str(manip.func(*numbers))
            self.dump_counters[manip.name] = str(manip.func(*numbers))

    def get_counter(self, name, strict=False):
        matched_keys = []
        try:
            matched_keys = list(filter(lambda k: k.endswith(name), self.keys()))
        except:
            matched_keys.append(name)
            
        if len(matched_keys) == 0:
            return 0
        if len(matched_keys) > 1:
            # print(f"more than one found for {name}, merging all value")
            total_value = sum([int(self.raw_counters[k]) for k in matched_keys])
            return total_value
        else:
            return self.raw_counters[matched_keys[0]]
    def get_dump_counters(self, name):
        return self.dump_counters[name]
        
    def get_counters(self):
        return self.raw_counters

    def keys(self):
        return list(self.raw_counters.keys())

    def __getitem__(self, index):
        return self.get_counter(index)

    def __iter__(self):
        return self.raw_counters.__iter__()

def get_prefix_length(names):
    return len(os.path.commonprefix(names))

def merge_perf_counters(all_manip,all_perf, verbose=False):
    def extract_numbers(s):
        re_digits = re.compile(r"(\d+)")
        pieces = re_digits.split(s)
        # convert int strings to int
        pieces = list(map(lambda x: int(x) if x.isdecimal() else x.lower(), pieces))
        return pieces
    all_names = sorted(list(set().union(*list(map(lambda s: s.keys(), all_perf)))), key=extract_numbers)
    all_perf = sorted(all_perf, key=lambda x: extract_numbers(x.filename))

    filenames = list(map(lambda x: x.filename, all_perf))
    # remove common prefix
    prefix_length = get_prefix_length(filenames) if len(filenames) > 1 else 0
    if prefix_length > 0:
        filenames = list(map(lambda name: name[prefix_length:], filenames))
    # remove common suffix
    reversed_names = list(map(lambda x: x[::-1], filenames))
    suffix_length = get_prefix_length(reversed_names) if len(filenames) > 1 else 0
    if suffix_length > 0:
        filenames = list(map(lambda name: name[:-suffix_length], filenames))
    all_sources = filenames

    all_manip_keys = [k.name for k in all_manip]
    
    yield ["trace","prefetcher"] + list(all_perf[0].dump_counters.keys())

    pbar = tqdm(total = len(all_names), disable = not verbose, position = 3)

    
    for dumpP in all_perf:
        yield [dumpP.filename,dumpP.flag_id] + list(dumpP.dump_counters.values())

def pick(include_names, name, include_manip = False):
    '''
        Filter output rows by name
    '''
    if len(include_names) == 0:
        return True
    if name == "header.cases": # First row is header, should always be true
        return True
    if include_manip and name.startswith("global."):
        return True
    for r in include_names:
        if r.search(name) != None:
            return True
    return False

def perf_work(manip, work_queue, perf_queue):
    while not work_queue.empty():
        item = work_queue.get()
        perf = PerfCounters(item)
        perf.add_manip(manip)
        perf_queue.put(perf)

def find_simulator_err(base_path):
    all_files = []
    for sub_dir in os.listdir(base_path):
        sub_path = os.path.join(base_path, sub_dir)
        if os.path.isfile(sub_path) and sub_dir == "simulator_err.txt":
            all_files.append(sub_path)
        elif os.path.isdir(sub_path):
            all_files += find_simulator_err(sub_path)
    return all_files

def find_all_in_dir(dir_path):
    base_path = dir_path
    all_files = []
    for sub_dir in os.listdir(base_path):
        sub_path = os.path.join(base_path, sub_dir)
        if os.path.isfile(sub_path):
            all_files.append(sub_path)
        else:
            print("find non-file " + sub_path)
    return all_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='performance counter log parser')
    parser.add_argument('--pfiles', metavar='filename', type=str, nargs='*', default=None,
                        help='performance counter log')
    parser.add_argument('--output', '-o', default="stats.csv", help='output file')
    parser.add_argument('--filelist', '-f', default=None, help="filelist")
    parser.add_argument('--recursive', '-r', action='store_true', default=False,
        help="recursively find simulator_err.txt")
    parser.add_argument('--dir', '-d', default = None, help="directory")
    parser.add_argument('--spec_json', '-S', default = None, help="spec test json")
    parser.add_argument('--verbose', '-v', action='store_true', default=False,
        help="show processing logs")
    parser.add_argument('--include', '-I', action='extend', nargs='+', type=str, help="select given counters (using re)")
    parser.add_argument('--manip', '-M', action='store_true', default=False, help="whether inlcude the manipulations in the res (for --include args)")
    parser.add_argument('--jobs', '-j', default=8, type=int, help="processing files in 'j' threads")
    parser.add_argument('--all', action='store_true', default=False,help="recursively analysis all directories")
    parser.add_argument('--pf', action='store_true', default=False,help="only analysis prefetcher")
    args = parser.parse_args()
    
    pfiles = []
    
    if args.filelist is not None:
        with open(args.filelist) as f:
            pfiles = list(map(lambda x: x.strip(), f.readlines()))
 
    # for every file in SPEC tests
    if args.recursive:
        pfiles = find_simulator_err(args.pfiles)

    normalize_spec = dict()
    if args.dir is not None:
        if args.spec_json is not None:
            with open(args.spec_json) as f:
                normalize_spec = json.load(f)
        else:
            pfiles += find_all_in_dir(args.dir)

    if args.include is not None:
        args.include = list(map(lambda x: re.compile(x), args.include))
    else:
        args.include = list()

    print("input files:")
    for filename in pfiles:
        print(filename)
        if not os.path.isfile(filename):
            print(f"{filename} is not a file. Probably you need --recursive?")
            exit()

    print(f"output file: {args.output}")
    all_perf = []
    all_manip = get_all_manip(args)

    work_queue = Queue()
    perf_queue = Queue()
    process_lst = []
    
    if args.all:
        root_dir = args.dir
        data_dirList = [d for d in os.listdir(args.dir) if os.path.isdir(os.path.join(args.dir, d))]
        data_dirList = list(map(lambda x:os.path.join(args.dir, x),data_dirList))
        for batch_dir in data_dirList:
            batch_name = os.path.basename(batch_dir)
            pfiles += find_simulator_err(str(batch_dir))
            pfiles = list(filter(lambda k: os.path.basename(k) in batch_name, normalize_spec.keys()))
        
            if len(normalize_spec) > 0 and batch_dir is not None:
                for spec_name in normalize_spec.keys():
                    work_queue.put((batch_name,batch_dir, spec_name, normalize_spec))
            else:
                for filename in pfiles:
                    work_queue.put(filename)
    
    files_count = work_queue.qsize()
 
    for i in range(0, args.jobs):
        p = Process(target = perf_work, args=(all_manip, work_queue, perf_queue))
        process_lst.append(p)
        p.start()
    pbar = tqdm(total = files_count, disable = not args.verbose, position = 1)    
    perf_lst = []
    
    while len(perf_lst) != files_count:
      if args.verbose:
        pbar.display(f"Processing files with {args.jobs} threads ...", 0)
      perf = perf_queue.get()
      perf_lst.append(perf)
      
      if perf and perf.raw_counters:
        all_perf.append(perf)
      elif perf:
        pbar.write(f"{perf.filename} skipped because it is empty.")
      pbar.update(1)
      
    for p in process_lst:
      p.join()
    
    data = list(merge_perf_counters(all_manip, all_perf, args.verbose))
    df = pd.DataFrame(data[1:], columns=data[0])
    excel_path = args.output
    root_name = os.path.basename(args.dir)
    if os.path.exists(excel_path):
        with pd.ExcelFile(excel_path) as xls:
            sheets = xls.sheet_names
        original_name = os.path.basename(excel_path)
        counter = random.randint(0, 9999)
        if root_name in sheets:
            root_name = args.dir.split('/')
            root_name = f"{root_name[-3]}_{root_name[-2]}"
            # root_name = f"perf-{sheets[0]}_{counter}"
            # counter += 1
        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, sheet_name=root_name, index=False)
    else:
        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, sheet_name=root_name, index=False)
            
         
    # with open(args.output, 'w') as csvfile:
    #     csvwriter = csv.writer(csvfile)
    #     for output_row in merge_perf_counters(all_manip, all_perf, args.verbose):
    #         if pick(args.include, output_row[0], args.manip):
    #             csvwriter.writerow(output_row)
    # pbar.write(f"Finished processing {len(all_perf)} non-empty files.")

    print("fininshed")