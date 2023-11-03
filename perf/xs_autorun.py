#! /usr/bin/env python3

import argparse
import array
import json
import math
import os
import sys
import random
import shutil
import signal
import subprocess
import threading
import time
import psutil
from multiprocessing import Process, Queue
from colorama import Fore , init
import matplotlib.pyplot as plt
import numpy as np

import perf
import spec_score
import top_down_report
from gcpt_run_time_eval import *
from gcpt import GCPT
import AutoEmailAlert
import multiprocessing

TASKS_DIR = "SPEC06_EmuTasks_10_22_2021"
MAX_THREADS = 112 #int(multiprocessing.cpu_count()/2)
RUN_THREADS = 16
init(autoreset=True)
def get_perf_base_path():
  if os.path.isabs(TASKS_DIR):
    return TASKS_DIR
  return os.path.join(os.path.dirname("."), TASKS_DIR)

def load_all_gcpt(gcpt_path, json_path, threads, state_filter=None, xs_path=None, sorted_by=None):
  perf_filter = [
    ("l3cache_mpki_load",      lambda x: float(x) < 3),
    ("branch_prediction_mpki", lambda x: float(x) > 5),
  ]
  perf_filter = None
  all_gcpt = []
  with open(json_path) as f:
    data = json.load(f)
  hour_list=[]
  perf_base_path = get_perf_base_path()
  perf_base_path = get_perf_base_path()
  for benchspec in data:
    for point in data[benchspec]:
      weight = data[benchspec][point]
      hour = get_eval_hour(benchspec, point, weight)
      gcpt = GCPT(gcpt_path, perf_base_path, benchspec, point, weight, hour)
      if state_filter is None and perf_filter is None:
        all_gcpt.append(gcpt)
        continue
      perf_match, state_match = True, True
      if state_filter is not None:
        state_match = False
        if gcpt.get_state() in state_filter:
          state_match = True
      if state_match and perf_filter is not None:
        perf_path = gcpt.get_err_path()
        counters = perf.PerfCounters(perf_path)
        counters.add_manip(get_all_manip())
        for fit in perf_filter:
          if not fit[1](counters[fit[0]]):
            perf_match = False
      if perf_match and state_match:
        hour_list.append(hour)
        all_gcpt.append(gcpt)
  print(f"evaluate execute hours: {cal_exe_hours(hour_list, MAX_THREADS // threads)}")
  print(f"evaluate execute hours: {cal_exe_hours(hour_list, MAX_THREADS // threads)}")

  if sorted_by is not None:
    all_gcpt = sorted(all_gcpt, key=sorted_by)
    hour_list = [g.eval_run_hours for g in all_gcpt]
    print(f"opitimize execute hours: {cal_exe_hours(hour_list, MAX_THREADS // threads)}")
    print(f"opitimize execute hours: {cal_exe_hours(hour_list, MAX_THREADS // threads)}")
  
  dump_json = True
  dump_json = False
  if dump_json:
    json_dict = dict()
    for gcpt in all_gcpt:
      bench_dict = json_dict.get(gcpt.benchspec, dict())
      bench_dict[gcpt.point] = gcpt.weight
      json_dict[gcpt.benchspec] = bench_dict
    with open("gcpt.json", "w") as f:
      json.dump(json_dict, f)
  return all_gcpt

pending_proc, error_proc = [], []

def get_available_threads():
  cpu_percentages = psutil.cpu_percent(interval = 1,percpu=True)
  free_threads = [1] * (int(MAX_THREADS))
  for i, percentage in enumerate(cpu_percentages)  :
    if i < MAX_THREADS:
      coreId = i
      if percentage < 5:
        free_threads[coreId] = 0

  return free_threads
  
def get_free_cores(free_threads):
  sequence_len = RUN_THREADS
  start_positions = []
  i=0
  while i < len(free_threads) - sequence_len + 1:
      curr_slice = free_threads[i:i+sequence_len]
      if  curr_slice.count(1) <= 1:
          start_positions.append(i)
          i += sequence_len  
      else:
          i += 1

  start_positions = [math.ceil(pos / RUN_THREADS) * RUN_THREADS for pos in start_positions]
  free_cores = [pos // RUN_THREADS for pos in start_positions]

  return free_cores

def xs_run(workloads, xs_path ,emu_path, warmup, max_instr, threads, cmdline_opt):
  nemu_so_path = os.path.join(xs_path, "ready-to-run/riscv64-nemu-interpreter-so")
  #nemu_so_path = os.path.join(xs_path, "ready-to-run/riscv64-spike-so")
  base_arguments = []
  if cmdline_opt == "nanhu":
    base_arguments = [emu_path, '--diff', nemu_so_path, '-W', str(warmup), '-I', str(max_instr), '-i']
  elif cmdline_opt == "kunminghu":
    base_arguments = [emu_path, '--diff', nemu_so_path, '--dump-db', '--enable-fork', '-W', str(warmup), '-I', str(max_instr), '-i']
  elif cmdline_opt == "nutshell":
    base_arguments = [emu_path, '--diff', nemu_so_path, '-I', str(max_instr), '-i']
  else:
    sys.exit("unsupported xs emu command line options, use nanhu or kunminghu")
  # base_arguments = [emu_path, '-W', str(warmup), '-I', str(max_instr), '-i']
  proc_count, finish_count = 0, 0
  free_threads = get_available_threads()
  free_cores = get_free_cores(free_threads)
  max_pending_proc = len(free_cores)
  can_launch = max_pending_proc
  # skip CI cores
  ci_cores = []#list(range(0, 64))# + list(range(32, 48))
  for core in list(map(lambda x: x // threads, ci_cores)):
    if core in free_cores:
      free_cores.remove(core)
      max_pending_proc -= 1
      
  start_time = time.time()
  timeStamp=0
  try:
    while len(workloads) > 0 or len(pending_proc) > 0:        
      has_pending_workload = len(workloads) > 0 and len(pending_proc) >= max_pending_proc
      has_pending_proc = len(pending_proc) > 0
      # deal when finished, update avaliable cores
      if has_pending_workload or has_pending_proc:
          # fisrt check pythisc core status
          free_threads = get_available_threads()
          free_cores = get_free_cores(free_threads)
          if timeStamp > random.uniform(120,150):
            max_pending_proc = len(free_cores)
            can_launch = max_pending_proc
            print(f"free_cores:{free_cores} max_pending_proc:{max_pending_proc} pending_proc_nums:{len(pending_proc)} can_lanuch:{can_launch}")
            timeStamp = 0
          timeStamp+=1
        
          finished_proc = list(filter(lambda p: p[1].poll() is not None, pending_proc))
          for workload, proc, core in finished_proc:
            pending_proc.remove((workload, proc, core))
            print(Fore.GREEN+f"{workload} has finished\n")
            if core not in free_cores:
              free_cores.append(core)
            if proc.returncode != 0:
              print(Fore.RED+f"[ERROR] {workload} exits with code {proc.returncode}")
              error_proc.append(workload)
            finish_count += 1
            can_launch += 1
      
      if can_launch < 0 or max_pending_proc < 0:
        continue

      for workload in workloads[:can_launch]:
        if len(free_cores) != 0:   
          numa_cmd = []
          workload_path = workload.get_bin_path()
          result_path = workload.get_res_dir()
          stdout_file = workload.get_out_path()
          stderr_file = workload.get_err_path()
          skip = False
          if not os.path.exists(result_path):
            os.makedirs(result_path, exist_ok=False)
          elif not args.override:
            if os.path.exists(stderr_file) and os.path.exists(stdout_file):
              # check if previous finined 
              with open(stdout_file, 'r') as f:
                content = f.read()
                if "ABORT" not in content.upper() and "IPC = -nan" not in content and "Host time spent:" in content:
                    print(Fore.RED + f"cmd {proc_count}: previous sim not finished ,resiming...")
                    skip=False
                # else :
                    #print(f"cmd {proc_count}: {numa_cmd+base_arguments+[workload_path]} need override")
                    
          if not skip:
            allocate_core = free_cores[-1]
            free_cores = free_cores[:-1]
            if threads > 1:
              start_core = threads * allocate_core
              end_core = threads * allocate_core + threads - 1
              numa_node = 1 if start_core >= 64 else 0
              numa_cmd = ["numactl", "-m", str(numa_node), "-C", f"{start_core}-{end_core}"]
            
            with open(stdout_file, "w") as stdout, open(stderr_file, "w") as stderr:
              random_seed = random.randint(0, 9999)
              run_cmd = numa_cmd + base_arguments + [workload_path] + ["-s", f"{random_seed}"]
              cmd_str = " ".join(run_cmd)
              print(f"cmd {proc_count}: {cmd_str}")
              proc = subprocess.Popen(run_cmd, stdout=stdout, stderr=stderr, preexec_fn=os.setsid)
              pending_proc.append((workload, proc, allocate_core))
              timeStamp = 0
              
          proc_count += 1 
    
      workloads = workloads[can_launch:]
      can_launch=0
      time.sleep(1)
          
  except KeyboardInterrupt:
    print("Interrupted. Exiting all programs ...")
    print("Not finished:")
    for i, (workload, proc, _) in enumerate(pending_proc):
      os.killpg(os.getpgid(proc.pid), signal.SIGINT)
      print(f"  ({i + 1}) {workload}")
    print("Not started:")
    for i, workload in enumerate(workloads):
      print(f"  ({i + 1}) {workload}")
  if len(error_proc) > 0:
    print("Errors:")
    for i, workload in enumerate(error_proc):
      print(f"  ({i + 1}) {workload}")
  used_time = time.time() - start_time
  print(Fore.GREEN+f"[{used_time/60:.2f} min]")


def get_all_manip():
    all_manip = []
    ipc = perf.PerfManip(
        name = "IPC",
        counters = [f"clock_cycle", f"commitInstr"],
        func = lambda cycle, instr: instr * 1.0 / cycle
    )
    all_manip.append(ipc)
    l3cache_mpki_load = perf.PerfManip(
      name = "global.l3cache_mpki_load",
      counters = [
          "L3_bank_0_A_channel_AcquireBlock_fire", "L3_bank_0_A_channel_Get_fire",
          "L3_bank_1_A_channel_AcquireBlock_fire", "L3_bank_1_A_channel_Get_fire",
          "L3_bank_2_A_channel_AcquireBlock_fire", "L3_bank_2_A_channel_Get_fire",
          "L3_bank_3_A_channel_AcquireBlock_fire", "L3_bank_3_A_channel_Get_fire",
          "commitInstr"
      ],
      func = lambda fire1, fire2, fire3, fire4, fire5, fire6, fire7, fire8, instr :
          1000 * (fire1 + fire2 + fire3 + fire4 + fire5 + fire6 + fire7 + fire8) / instr
    )
    all_manip.append(l3cache_mpki_load)
    branch_mpki = perf.PerfManip(
      name = "global.branch_prediction_mpki",
      counters = ["ftq.BpWrong", "commitInstr"],
      func = lambda wrong, instr: 1000 * wrong / instr
    )
    all_manip.append(branch_mpki)
    return all_manip

def get_total_inst(benchspec, spec_version, isa):
  base_dir = "/nfs/share/checkpoints_profiles"
  if spec_version == 2006:
    if isa == "rv64gc_old":
      base_path = os.path.join(base_dir, "spec06_rv64gc_o2_50m/profiling")
      filename = "nemu_out.txt"
      bench_path = os.path.join(base_path, benchspec, filename)
    elif isa == "rv64gc":
      base_path = os.path.join(base_dir, "spec06_rv64gc_o2_20m/logs/profiling/")
      filename = benchspec + ".log"
      bench_path = os.path.join(base_path, filename)
    elif isa == "rv64gcb":
      base_path = os.path.join(base_dir, "spec06_rv64gcb_o2_20m/logs/profiling/")
      filename = benchspec + ".log"
      bench_path = os.path.join(base_path, filename)
    elif isa == "rv64gcb_o3":
      base_path = os.path.join(base_dir, "spec06_rv64gcb_o3_20m/logs/profiling/")
      filename = benchspec + ".log"
      bench_path = os.path.join(base_path, filename)
    else:
      print("Unknown ISA\n")
      return None
  elif spec_version == 2017:
    if isa == "rv64gc_old":
      base_path = os.path.join(base_dir, "spec17_rv64gc_o2_50m/profiling")
      filename = "nemu_out.txt"
      bench_path = os.path.join(base_path, benchspec, filename)
    elif isa == "rv64gcb":
      base_path = os.path.join(base_dir, "spec17_rv64gcb_o2_20m/logs/profiling/")
      filename = benchspec + ".log"
      bench_path = os.path.join(base_path, filename)
    elif isa == "rv64gcb_o3":
      base_path = os.path.join(base_dir, "spec17_rv64gcb_o3_20m/logs/profiling/")
      filename = benchspec + ".log"
      bench_path = os.path.join(base_path, filename)
    else:
      print("Unknown ISA\n")
      return None
  else:
    print("Unknown SPEC version\n")
    return None
  f = open(bench_path)
  for line in f:
    if "total guest instructions" in line:
      f.close()
      return int(line.split("instructions = ")[1].replace("\x1b[0m", ""))
  return None



def xs_report_ipc(xs_path, gcpt_queue, result_queue):
  while not gcpt_queue.empty():
    gcpt = gcpt_queue.get()
    # print(f"Processing {str(gcpt)}...")
    perf_path = gcpt.get_err_path()
    counters = perf.PerfCounters(perf_path)
    counters.add_manip(get_all_manip())
    # when the spec has not finished, IPC may be None
    if counters["IPC"] is not None:
      result_queue.put([gcpt.benchspec, [float(gcpt.weight), float(counters["IPC"])]])
    else:
      print("IPC not found in", gcpt.benchspec, gcpt.point, gcpt.weight)

def xs_report(all_gcpt, xs_path, spec_version, isa, num_jobs,enPrint= True):
  # frequency/GHz
  frequency = 2
  gcpt_ipc = dict()
  keys = list(map(lambda gcpt: gcpt.benchspec, all_gcpt))
  for k in keys:
    gcpt_ipc[k] = []
  # multi-threading for processing the performance counters
  gcpt_queue = Queue()
  for gcpt in all_gcpt:
    gcpt_queue.put(gcpt)
  result_queue = Queue()
  process_list = []
  for _ in range(num_jobs):
    p = Process(target=xs_report_ipc, args=(xs_path, gcpt_queue, result_queue))
    process_list.append(p)
    p.start()
  for p in process_list:
    p.join()
  while not result_queue.empty():
    result = result_queue.get()
    gcpt_ipc[result[0]].append(result[1])
  if enPrint:
    print("=================== Coverage ==================")
  spec_time = {}
  for benchspec in gcpt_ipc:
    total_weight = sum(map(lambda info: info[0], gcpt_ipc[benchspec]))
    total_cpi = sum(map(lambda info: info[0] / info[1], gcpt_ipc[benchspec])) / total_weight
    num_instr = get_total_inst(benchspec, spec_version, isa)
    num_seconds = total_cpi * num_instr / (frequency * (10 ** 9))
    if enPrint:
      print(f"{benchspec:>25} coverage: {total_weight:.2f}")
    spec_name = benchspec.split("_")[0]
    spec_time[spec_name] = spec_time.get(spec_name, 0) + num_seconds
  print()
  spec_score.get_spec_score(args,spec_time, spec_version, frequency, enPrint)
  if enPrint:
    print(f"Number of Checkpoints: {len(all_gcpt)}")
    print(f"SPEC CPU Version: SPEC CPU{spec_version}, {isa}")

def xs_report_top_down(all_gcpt, xs_path, spec_version, isa, num_jobs):
  gcpt_top_down = dict()
  keys = list(map(lambda gcpt: gcpt.benchspec, all_gcpt))
  for k in keys:
    gcpt_top_down[k.split("_")[0]] = dict()
  graph_num = top_down_report.xs_report_top_down_tf(get_perf_base_path, all_gcpt, gcpt_top_down)
  plt.figure(figsize=(25,45))
  for i in range(graph_num):
    plt.subplot((graph_num + 1) // 2, 2, i + 1)
    matrix = []
    name = []
    boundname = []
    topname = ''
    for benchspec,top in gcpt_top_down.items():
      top = top[i]
      lst = []
      name.append(benchspec)
      topname = top.name
      for value in top.down:
        boundname.append(value.name)
        lst.append(value.percentage)
      matrix.append(lst)
    matrix = list(np.array(matrix).T)

    bottom = [0.0] * len(matrix[0])
    for zipped in zip(boundname, matrix):
      plt.bar(name, zipped[1], bottom=bottom, label=zipped[0])
      bottom = list(map(lambda x,y: x + y, bottom, zipped[1]))
    plt.xticks(rotation=90)
    plt.legend()
    plt.title(topname)
  plt.savefig(f'{get_perf_base_path()}_topdown.svg', bbox_inches='tight')
  plt.savefig(f'{get_perf_base_path()}_topdown.svg', bbox_inches='tight')
  # for benchspec,top in gcpt_top_down.items():
  #   bottom = [0.0]
  #   for key,value in top.down.items():
  #     percentage = [value.percentage]
  #     plt.bar([benchspec], percentage, bottom=bottom, label=key)
  #     bottom = list(map(lambda x,y: x + y, bottom, percentage))
  # plt.legend()
  # plt.savefig(f'{get_perf_base_path()}_topdown/{top.name}.png')
  # plt.savefig(f'{get_perf_base_path()}_topdown/{top.name}.png')
  # plt.clf()
  #print(f"Number of Checkpoints: {len(all_gcpt)}")
  #print(f"SPEC CPU Version: SPEC CPU{spec_version}, {isa}")


def xs_show(all_gcpt):
  i=0
  i=0
  for gcpt in all_gcpt:
    gcpt.show(i)
    i+=1
    gcpt.show(i)
    i+=1

def xs_debug(all_gcpt):
  for gcpt in all_gcpt:
    gcpt.debug()

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="autorun script for xs")
  parser.add_argument('--gcpt_path', metavar='gcpt_path', type=str,
                      help='path to gcpt checkpoints',default="/nfs/share/checkpoints_profiles/spec06_rv64gcb_o2_20m/take_cpt")
  parser.add_argument('--json_path', metavar='json_path', type=str,
                      help='path to gcpt json',default="/nfs/share/checkpoints_profiles/spec06_rv64gcb_o2_20m/json/simpoint_coverage0.3_test.json")
  parser.add_argument('--xs',type=str, help='path to xs')
  parser.add_argument('--emu', help='path to emu',default=f"./build/emu")
  parser.add_argument('--cmdline-opt', default="nanhu", type=str, help='xs emu command line options, nanhu or kunminghu')
  parser.add_argument('--ref', default=None, type=str, help='path to ref')
  parser.add_argument('--warmup', '-W', default=5000000, type=int, help="warmup instr count")
  parser.add_argument('--max-instr', '-I', default=20000000, type=int, help="max instr count")
  parser.add_argument('--threads', '-T', default=16, type=int, help="number of emu threads")
  parser.add_argument('--maxthreads', '-t', default=0, type=int, help="number of emu threads")
  parser.add_argument('--report', '-R', action='store_true', default=False, help='report only')
  parser.add_argument('--report-top-down', action='store_true', default=False, help='report top-down only')
  parser.add_argument('--show', '-S', action='store_true', default=False, help='show list of gcpt only')
  parser.add_argument('--debug', '-D', action='store_true', default=False, help='debug options')
  parser.add_argument('--version', default=2006, type=int, help='SPEC version')
  parser.add_argument('--isa', default="rv64gcb", type=str, help='ISA version')
  parser.add_argument('--slice', help='select only some checkpoints (only for run)')
  parser.add_argument('--dir', default=None, type=str, help='SPECTasks dir')
  parser.add_argument('--jobs', '-j', default=1, type=int, help="processing files in 'j' threads")
  parser.add_argument('--override', action='store_true', default=False, help="continue to exe, ignore the aborted and success tests")
  parser.add_argument('--pf', action='store_true', default=False, help="specify for prefetcher")
  parser.add_argument('--pfFast', action='store_true', default=False, help="specify for prefetcher fast")
  parser.add_argument('--all', action='store_true', default=False, help="report regression for specify directory's all subdirectories ")

  args = parser.parse_args()
  print(args)
  
  if args.maxthreads != 0:
    MAX_THREADS = args.maxthreads
  if args.threads != RUN_THREADS:
    RUN_THREADS = args.threads
  
  if args.pf:
    args.json_path=os.path.abspath("config/prefetch_simpoint_coverage0.3_test.json")
  if args.pfFast:
    args.json_path=os.path.abspath("config/prefetchFast_simpoint_coverage0.3_test.json")
    
  if args.dir is not None:
    TASKS_DIR = args.dir

  if args.ref is None:
    args.ref = args.xs

  if args.show:
    gcpt = load_all_gcpt(args.gcpt_path, args.json_path, args.threads, xs_path=args.xs, sorted_by=lambda x: -x.eval_run_hours)
    #gcpt = load_all_gcpt(args.gcpt_path, args.json_path, args.threads, 
      #state_filter=[GCPT.STATE_FINISHED], xs_path=args.ref, sorted_by=lambda x: x.get_simulation_cps())
      #state_filter=[GCPT.STATE_ABORTED], xs_path=args.ref, sorted_by=lambda x: x.get_ipc())
      #state_filter=[GCPT.STATE_ABORTED], xs_path=args.ref, sorted_by=lambda x: x.benchspec.lower())
      #state_filter=[GCPT.STATE_RUNNING], xs_path=args.ref, sorted_by=lambda x: x.benchspec.lower())
      #state_filter=[GCPT.STATE_FINISHED], xs_path=args.ref, sorted_by=lambda x: -x.num_cycles)
      #state_filter=[GCPT.STATE_ABORTED], xs_path=args.ref, sorted_by=lambda x: -x.num_cycles)
    xs_show(gcpt)
  elif args.debug:
    gcpt = load_all_gcpt(args.gcpt_path, args.json_path, args.threads, 
      state_filter=[GCPT.STATE_ABORTED], xs_path=args.ref, sorted_by=lambda x: -x.num_cycles)
    xs_debug(gcpt)
  elif args.report:
    if args.all:
      root_dir = args.dir
      data_dirList = [dirs for dirs in os.listdir(args.dir) if os.path.isdir(os.path.join(args.dir, dirs))]
      for batchDir in data_dirList:
        TASKS_DIR = os.path.abspath(f"{root_dir}/{batchDir}/")
        args.dir = TASKS_DIR
        gcpt = load_all_gcpt(args.gcpt_path, args.json_path, args.threads, 
          state_filter=[GCPT.STATE_FINISHED], xs_path=None, sorted_by=lambda x: x.benchspec.lower())
        if gcpt:
          print(f"------------------------------------------------------------\n{TASKS_DIR}")
          xs_report(gcpt, args.ref, args.version, args.isa, args.jobs,enPrint=False)
    else:
      gcpt = load_all_gcpt(args.gcpt_path, args.json_path, args.threads, 
        state_filter=[GCPT.STATE_FINISHED], xs_path=args.ref, sorted_by=lambda x: x.benchspec.lower())
      xs_report(gcpt, args.ref, args.version, args.isa, args.jobs)
  elif args.report_top_down:
    gcpt = load_all_gcpt(args.gcpt_path, args.json_path, args.threads, 
      state_filter=[GCPT.STATE_FINISHED], xs_path=args.ref, sorted_by=lambda x: x.benchspec.lower())
    xs_report_top_down(gcpt, args.ref, args.version, args.isa, args.jobs)
  else:
    state_filter = None
    if (not args.override):
      state_filter = [GCPT.STATE_ABORTED, GCPT.STATE_RUNNING, GCPT.STATE_NONE]
      
    # If just wanna run aborted test, change the script.
    gcpt = load_all_gcpt(args.gcpt_path, args.json_path, args.threads, 
                         state_filter=state_filter, 
                         xs_path=args.xs, 
                         sorted_by=lambda x: -x.eval_run_hours
                         )

    if (len(gcpt) == 0):
      print("All the tests are already finished.")
      print(f"perf_base_path: {get_perf_base_path()}")
      sys.exit()
    if args.slice:
      start, end = args.slice.split(":")
      if not start:
        start = 0
      if not end:
        end = len(gcpt)
      start, end = int(start), int(end)
      print(f"select gcpt[{start}:{end}]")
      gcpt = gcpt[start:end]
    print("All:  ", len(gcpt))
    print("First:", gcpt[0])
    print("Last: ", gcpt[-1])
    input("Please check and press enter to continue")
    xs_run(gcpt, args.xs, args.emu, args.warmup, args.max_instr, args.threads, args.cmdline_opt)
    
    # AutoEmailAlert.inform(0, f"{args.xs}执行完毕", "huanghualiwood@163.com")