#! /usr/bin/env python3

"""
    Parameter ratio indicators are defined classes, including 
    the name of the performance parameter, 
    the performance counter to be probed, 
    and the lamda expression to be calculated
"""
class PerfManip(object):
    def __init__(self, name, counters = None, func = None, get_base = False, pattern = "", get_bool= False):
        self.name = name
        self.counters = counters
        if func is None and len(counters) == 1:
            self.func = lambda x:x
        else:
            self.func = func
        self.get_base = get_base
        self.pattern = pattern
        self.get_bool = get_bool
    def __str__(self):
            return f"{self.name}: Counters: {self.counters}"
        
def get_rs_manip():
    all_manip = []
    alu_bypass_from_mdu = PerfManip(
        name = "global.rs.alu_bypass_from_mdu",
        counters = [
            "exuBlocks.scheduler.issue_fire",
            "exuBlocks.scheduler.rs.source_bypass_6_0",
            "exuBlocks.scheduler.rs.source_bypass_6_1",
            "exuBlocks.scheduler.rs.source_bypass_6_2",
            "exuBlocks.scheduler.rs.source_bypass_6_3",
            "exuBlocks.scheduler.rs.source_bypass_7_0",
            "exuBlocks.scheduler.rs.source_bypass_7_1",
            "exuBlocks.scheduler.rs.source_bypass_7_2",
            "exuBlocks.scheduler.rs.source_bypass_7_3"
        ],
        func = lambda fire, b60, b61, b62, b63, b70, b71, b72, b3: (b60 + b61 + b62 + b63 + b70 + b71 + b72 + b3)# / fire
    )
    # all_manip.append(alu_bypass_from_mdu)
    mdu_bypass_from_mdu = PerfManip(
        name = "global.rs.mdu_bypass_from_mdu",
        counters = [
            "exuBlocks_1.scheduler.rs.deq_fire_0",
            "exuBlocks_1.scheduler.rs.deq_fire_1",
            "exuBlocks_1.scheduler.rs.source_bypass_4_0",
            "exuBlocks_1.scheduler.rs.source_bypass_4_1",
            "exuBlocks_1.scheduler.rs.source_bypass_5_0",
            "exuBlocks_1.scheduler.rs.source_bypass_5_1"
        ],
        func = lambda fire0, fire1, b40, b41, b50, b51: (b40 + b41 + b50 + b51)# / (fire0 + fire1)# if (fire0 + fire1) > 0 else 0
    )
    # all_manip.append(mdu_bypass_from_mdu)
    load_bypass_from_mdu = PerfManip(
        name = "global.rs.load_bypass_from_mdu",
        counters = [
            "memScheduler.rs.deq_fire_0",
            "memScheduler.rs.deq_fire_1",
            "memScheduler.rs.source_bypass_6_0",
            "memScheduler.rs.source_bypass_6_1",
            "memScheduler.rs.source_bypass_7_0",
            "memScheduler.rs.source_bypass_7_1"
        ],
        func = lambda fire0, fire1, b60, b61, b70, b71: (b60 + b61 + b70 + b71)# / (fire0 + fire1)# if (fire0 + fire1) > 0 else 0
    )
    # all_manip.append(load_bypass_from_mdu)
    alu_issue_exceed_limit = PerfManip(
        name = "global.rs.alu_issue_exceed_limit",
        counters = [
            "exuBlocks.scheduler.rs.rs_0.statusArray.not_selected_entries",
            "exuBlocks.scheduler.rs.rs_1.statusArray.not_selected_entries",
            "ctrlBlock.rob.clock_cycle"
        ],
        func = lambda ex0, ex1, cycle : (ex0 + ex1) / cycle
    )
    # all_manip.append(alu_issue_exceed_limit)
    alu_issue_exceed_limit_instr = PerfManip(
        name = "global.rs.alu_issue_exceed_limit_instr",
        counters = [
            "exuBlocks.scheduler.rs.rs_0.statusArray.not_selected_entries",
            "exuBlocks.scheduler.rs.rs_1.statusArray.not_selected_entries",
            "exuBlocks.scheduler.issue_fire"
        ],
        func = lambda ex0, ex1, cycle : (ex0 + ex1) / cycle
    )
    # all_manip.append(alu_issue_exceed_limit_instr)
    return all_manip

def get_fu_manip():
    all_manip = []
    div_0_in_blocked = PerfManip(
        name = "global.fu.div_0_in_blocked",
        counters = ["exeUnits_0.div.in_fire", "exeUnits_0.div.in_valid"],
        func = lambda f, v: (v - f) / v if v != 0 else 0
    )
    all_manip.append(div_0_in_blocked)
    div_1_in_blocked = PerfManip(
        name = "global.fu.div_1_in_blocked",
        counters = ["exeUnits_1.div.in_fire", "exeUnits_1.div.in_valid"],
        func = lambda f, v: (v - f) / v if v != 0 else 0
    )
    all_manip.append(div_1_in_blocked)
    mul_0_in_blocked = PerfManip(
        name = "global.fu.mul_0_in_blocked",
        counters = ["exeUnits_0.mul.in_fire", "exeUnits_0.mul.in_valid"],
        func = lambda f, v: (v - f) / v if v != 0 else 0
    )
    all_manip.append(mul_0_in_blocked)
    mul_1_in_blocked = PerfManip(
        name = "global.fu.mul_1_in_blocked",
        counters = ["exeUnits_1.mul.in_fire", "exeUnits_1.mul.in_valid"],
        func = lambda f, v: (v - f) / v if v != 0 else 0
    )
    all_manip.append(mul_1_in_blocked)
    i2f_in_blocked = PerfManip(
        name = "global.fu.i2f_in_blocked",
        counters = ["exeUnits_2.i2f.in_fire", "exeUnits_2.i2f.in_valid"],
        func = lambda f, v: (v - f) / v if v != 0 else 0
    )
    all_manip.append(i2f_in_blocked)
    f2i_0_in_blocked = PerfManip(
        name = "global.fu.f2i_0_in_blocked",
        counters = ["exeUnits_4.f2i.in_fire", "exeUnits_4.f2i.in_fire"],
        func = lambda f, v: (v - f) / v if v != 0 else 0
    )
    all_manip.append(f2i_0_in_blocked)
    f2i_1_in_blocked = PerfManip(
        name = "global.fu.f2i_1_in_blocked",
        counters = ["exeUnits_5.f2i.in_fire", "exeUnits_5.f2i.in_valid"],
        func = lambda f, v: (v - f) / v if v != 0 else 0
    )
    all_manip.append(f2i_1_in_blocked)
    f2f_0_in_blocked = PerfManip(
        name = "global.fu.f2f_0_in_blocked",
        counters = ["exeUnits_4.f2f.in_fire", "exeUnits_4.f2f.in_fire"],
        func = lambda f, v: (v - f) / v if v != 0 else 0
    )
    all_manip.append(f2f_0_in_blocked)
    f2f_1_in_blocked = PerfManip(
        name = "global.fu.f2f_1_in_blocked",
        counters = ["exeUnits_5.f2f.in_fire", "exeUnits_5.f2f.in_valid"],
        func = lambda f, v: (v - f) / v if v != 0 else 0
    )
    all_manip.append(f2f_1_in_blocked)
    fdiv_sqrt_0_in_blocked = PerfManip(
        name = "global.fu.fdiv_sqrt_0_in_blocked",
        counters = ["exeUnits_4.fdivSqrt.in_fire", "exeUnits_4.fdivSqrt.in_valid"],
        func = lambda f, v: (v - f) / v if v != 0 else 0
    )
    all_manip.append(fdiv_sqrt_0_in_blocked)
    fdiv_sqrt_1_in_blocked = PerfManip(
        name = "global.fu.fdiv_sqrt_1_in_blocked",
        counters = ["exeUnits_5.fdivSqrt.in_fire", "exeUnits_5.fdivSqrt.in_valid"],
        func = lambda f, v: (v - f) / v if v != 0 else 0
    )
    all_manip.append(fdiv_sqrt_1_in_blocked)
    load_0_in_blocked = PerfManip(
        name = "global.fu.load_0_in_blocked",
        counters = ["memScheduler.rs.deq_fire_0", "memScheduler.rs.deq_valid_0"],
        func = lambda f, v: (v - f) / v if v != 0 else 0
    )
    # all_manip.append(load_0_in_blocked)
    load_1_in_blocked = PerfManip(
        name = "global.fu.load_1_in_blocked",
        counters = ["memScheduler.rs.deq_fire_1", "memScheduler.rs.deq_valid_1"],
        func = lambda f, v: (v - f) / v if v != 0 else 0
    )
    # all_manip.append(load_1_in_blocked)
    load_replay_frac = PerfManip(
        name = "global.fu.load_replay_frac",
        counters = ["memScheduler.rs.deq_fire_0", "memScheduler.rs.deq_fire_1", "memScheduler.rs.deq_not_first_issue_0", "memScheduler.rs.deq_not_first_issue_1"],
        func = lambda f0, f1, r0, r1: (r0 + r1) / (f0 + f1) if (f0 + f1) != 0 else 0
    )
    # all_manip.append(load_replay_frac)
    store_replay_frac = PerfManip(
        name = "global.fu.store_replay_frac",
        counters = ["memScheduler.rs_1.deq_fire_0", "memScheduler.rs_1.deq_fire_1", "memScheduler.rs_1.deq_not_first_issue_0", "memScheduler.rs_1.deq_not_first_issue_1"],
        func = lambda f0, f1, r0, r1: (r0 + r1) / (f0 + f1) if (f0 + f1) != 0 else 0
    )
    # all_manip.append(store_replay_frac)
    return all_manip

def get_wpu_manip():
    all_manip = []
    # Flip rate
    all_manip.append(PerfManip(
        name = "global.T_ICache",
        counters = [
            "icache.dataArray.data_read_counter",
            "ctrlBlock.rob.clock_cycle"
        ],
        func = lambda cnt, time: 512.0 * cnt / time
    ))
    all_manip.append(PerfManip(
        name = "global.T_DCache",
        counters = [
            "dcache.bankedDataArray.data_read_counter",
            "ctrlBlock.rob.clock_cycle"
        ],
        func = lambda cnt, time: 64.0 * cnt / time
    ))

    # iwpu precision
    all_manip.append(PerfManip(
        name = "global.iwpu_pred_precision",
        counters = [
            "icache.iwpu.wpu_pred_succ",
            "icache.iwpu.wpu_pred_total"
        ],
        func = lambda succ, total: 1.0 * succ / total
    ))
    all_manip.append(PerfManip(
        name = "global.iwpu_part_pred_precision",
        counters = [
            "icache.mainPipe.iwpu.wpu_pred_succ",
            "icache.mainPipe.iwpu.wpu_pred_total",
            "icache.replacePipe.iwpu.wpu_pred_succ",
            "icache.replacePipe.iwpu.wpu_pred_total",
        ],
        func = lambda succ1, total1, succ2, total2: 1.0 * (succ1 + succ2) / (total1 + total2)
    ))
    all_manip.append(PerfManip(
        name = "global.iwpu_part0_pred_precision",
        counters = [
            "icache.mainPipe.iwpu.wpu_pred_succ",
            "icache.mainPipe.iwpu.wpu_pred_total",
        ],
        func = lambda succ, total: 1.0 * succ / total
    ))
    all_manip.append(PerfManip(
        name = "global.iwpu_part1_pred_precision",
        counters = [
            "icache.replacePipe.iwpu.wpu_pred_succ",
            "icache.replacePipe.iwpu.wpu_pred_total",
        ],
        func = lambda succ, total: 1.0 * succ / total
    ))
    # dwpu precision
    all_manip.append(PerfManip(
        name = "global.dwpu_pred_precision",
        counters = [
            "dcache.dwpu.wpu_pred_succ",
            "dcache.dwpu.wpu_pred_total"
        ],
        func = lambda succ, total: 1.0 * succ / total
    ))
    all_manip.append(PerfManip(
        name = "global.dwpu_part_pred_precision",
        counters = [
            "dcache.ldu_0.dwpu.wpu_pred_succ",
            "dcache.ldu_0.dwpu.wpu_pred_total",
            "dcache.ldu_1.dwpu.wpu_pred_succ",
            "dcache.ldu_1.dwpu.wpu_pred_total",
        ],
        func = lambda succ1, total1, succ2, total2: (1.0 * succ1 / total1 + 1.0 * succ2 / total2) / 2
    ))
    all_manip.append(PerfManip(
        name = "global.dwpu_part0_pred_precision",
        counters = [
            "dcache.ldu_0.dwpu.wpu_pred_succ",
            "dcache.ldu_0.dwpu.wpu_pred_total",
        ],
        func = lambda succ, total: 1.0 * succ / total
    ))
    all_manip.append(PerfManip(
        name = "global.dwpu_part1_pred_precision",
        counters = [
            "dcache.ldu_1.dwpu.wpu_pred_succ",
            "dcache.ldu_1.dwpu.wpu_pred_total",
        ],
        func = lambda succ, total: 1.0 * succ / total
    ))
    # iwpu mpki
    all_manip.append(PerfManip(
        name = "global.iwpu_pred_mpki",
        counters = [
            "icache.iwpu.wpu_pred_fail",
            "commitInstr"
        ],
        func = lambda fail, instr: 1000.0 * fail / instr
    ))
    all_manip.append(PerfManip(
        name = "global.iwpu_part_pred_mpki",
        counters = [
            "icache.mainPipe.iwpu.wpu_pred_fail",
            "icache.replacePipe.iwpu.wpu_pred_fail",
            "commitInstr"
        ],
        func = lambda fail1, fail2, instr: 1000.0 * (fail1 + fail2) / instr
    ))
    all_manip.append(PerfManip(
        name = "global.iwpu_part0_pred_mpki",
        counters = [
            "icache.mainPipe.iwpu.wpu_pred_fail",
            "commitInstr"
        ],
        func = lambda fail, instr: 1000.0 * fail / instr
    ))
    all_manip.append(PerfManip(
        name = "global.iwpu_part1_pred_mpki",
        counters = [
            "icache.replacePipe.iwpu.wpu_pred_fail",
            "commitInstr"
        ],
        func = lambda fail, instr: 1000.0 * fail / instr
    ))
    # dwpu mpki
    all_manip.append(PerfManip(
        name = "global.dwpu_pred_mpki",
        counters = [
            "dcache.dwpu.wpu_pred_fail",
            "commitInstr"
        ],
        func = lambda fail, instr: 1000.0 * fail / instr
    ))
    all_manip.append(PerfManip(
        name = "global.dwpu_part_pred_mpki",
        counters = [
            "dcache.ldu_0.dwpu.wpu_pred_fail",
            "dcache.ldu_1.dwpu.wpu_pred_fail",
            "commitInstr"
        ],
        func = lambda fail1, fail2, instr: 1000.0 * (fail1 + fail2) / instr
    ))
    all_manip.append(PerfManip(
        name = "global.dwpu_part0_pred_mpki",
        counters = [
            "dcache.ldu_0.dwpu.wpu_pred_fail",
            "commitInstr"
        ],
        func = lambda fail, instr: 1000.0 * fail / instr
    ))
    all_manip.append(PerfManip(
        name = "global.dwpu_part1_pred_mpki",
        counters = [
            "dcache.ldu_1.dwpu.wpu_pred_fail",
            "commitInstr"
        ],
        func = lambda fail, instr: 1000.0 * fail / instr
    ))
    return all_manip


def get_base_manip():
    all_manip = []
    all_manip.append(PerfManip(
        name = "IPC",
        get_base=True,
        counters = [
            "IPC"
        ]
    ))
    all_manip.append(PerfManip(
        name = "instrCnt",
        get_base=True,
        counters = [
            "instrCnt"
        ]
    ))
    all_manip.append(PerfManip(
        name = "cycleCnt",
        get_base=True,
        counters = [
            "cycleCnt"
        ]
    ))
    all_manip.append(PerfManip(
        name = "STATE",
        get_base=True,
        get_bool=True,
        pattern="EXCEEDING CYCLE/INSTR LIMIT",
        func= lambda x : "finished" if x is True else "failed"
    ))
    all_manip.append(PerfManip(
        name = "simTime_hour",
        get_base=True,
        pattern="Host time spent: (\d+(,\d+)*)ms",
        func= lambda x : f"{x/(3600000):2f}"
    ))
    return all_manip

def get_l2_manip_cocotb():
    all_manip = []
    # Flip rate
    all_manip.append(PerfManip(
        name = "||-cov",
        counters = [
            "dirWrite_all","dirWrite_fromPrefetch"
        ],
        func = lambda x, y: y / (x + y + 1)
    ))
    all_manip.append(PerfManip(
        name = "||-A_normal_hitRate",
        counters = [
            "L2_a_normalAcquire_miss","L2_a_normalAcquire_hit"
        ],
        func = lambda x, y: y / (x + y)
    ))
    all_manip.append(PerfManip(
        name = "||-A_acquire_hitRate",
        counters = [
            "L2_a_req_hit","L2_a_req_miss"
        ],
        func = lambda hit, miss: hit / (hit + miss + 1)
    ))
    all_manip.append(PerfManip(
        name = "||-pfReq_missRate",
        counters = [
            "L2_a_pfReq_miss","L2_a_pfReq_hit"
        ],
        func = lambda x, y: x / (x + y+ 1)
    ))
    all_manip.append(PerfManip(
        name = "||-acquire_proportion",
        counters = [
            "L2_req_hit","L2_a_req_hit","L2_a_req_miss"
        ],
        func = lambda x, y1,y2: (y1+y2) / (x + y1 + y2 + 1)
    ))
    all_manip.append(PerfManip( #instr
        name = "||-req_getRate",
        counters = [
            "L2_a_get_hit","L2_a_get_miss"
        ],
        func = lambda hit, miss: hit / (hit + miss + 1)
    ))
    all_manip.append(PerfManip(
        name = "||-mshr_TaskHint_proportion",
        counters = [
            "mshr_hintack_req","mshr_accessackdata_req","mshr_probeackdata_req","mshr_grant_req","mshr_probeack_req","mshr_release_req"
        ],
        func = lambda x1, x2, x3, x4, x5, x6: x1 / (x1+x2+x3+x4+x5+x6+1)
    ))
    return all_manip

def get_prefetch_manip():
    all_manip = []
    all_manip.append(PerfManip(
        name = "||-pfTrain_Miss_proportion",
        counters = [
            "prefetch_train",
            "prefetch_train_on_miss"
        ],
        func = lambda all,miss: miss / (all + 1)
    ))
    all_manip.append(PerfManip(
        name = "||-pfFilter_passRate",
        counters = [
            "hyper_filter_input",
            "hyper_filter_output",
        ],
        func = lambda x,y : y /(x+y+1)
    ))    
    all_manip.append(PerfManip(
        name = "l2_prefetch_dead_block_nums",
        counters = [
            "prefetch_dead_block",
        ]
    ))
    all_manip.append(PerfManip(
        name = "l2_pfTop_PFReq_totals",
        counters = [
            "prefetch_send2_pfq",
        ]
    ))
    all_manip.append(PerfManip(
        name = "||-spp_proportion",
        counters = [
            "bop_send2_queue",
            "sms_send2_queue",
            "spp_send2_queue"
        ],
        func = lambda sms,bop,spp:  0 if (sms + bop + spp)==0 else spp / (sms + bop + spp)
    ))
    all_manip.append(PerfManip(
        name = "||-pf_overlapRate",
        counters = [
            "hyper_overlapped",
            "bop_send2_queue",
            "sms_send2_queue",
            "spp_send2_queue"
        ],
        func = lambda x,y1,y2,y3 : x/(y1+y2+y3+1)
    ))
    all_manip.append(PerfManip(
        name = "||-mp_acquire_pfTrain_MISS_proportion",
        counters = [
            "acquire_trigger_prefetch_on_miss",
            "a_req_trigger_prefetch",
        ],
        func = lambda x,y : x/(y+1)
    ))
    all_manip.append(PerfManip(
        name = "||-mp_acquire_pfTrain_HIT_proportion",
        counters = [
            "acquire_trigger_prefetch_on_hit_pft",
            "a_req_trigger_prefetch",
        ],
        func = lambda x,y : x/(y+1)
    ))
    all_manip.append(PerfManip(
        name = "||-mp_get_pfTrain_MISS_proportion",
        counters = [
            "get_trigger_prefetch_on_miss",
            "a_req_trigger_prefetch",
        ],
        func = lambda x,y : x/(y+1)
    ))   
    all_manip.append(PerfManip(
        name = "||-mp_get_pfTrain_HIT_proportion",
        counters = [
            "get_trigger_prefetch_on_hit_pft",
            "a_req_trigger_prefetch",
        ],
        func = lambda x,y : x/(y+1)
    ))  

    # 不能计算有效访问块占比
    all_manip.append(PerfManip(
        name = "||-mp_pf_deadBlock_proportion",
        counters = [
            "release_prefetch_not_accessed",
            "release_all",
        ],
        func = lambda x,y : x/(y+1)
    ))
    all_manip.append(PerfManip(
        name = "||-mp_pf_earlyPfRate",
        counters = [
            "early_prefetch",
            "mshr_hintack_req",
        ],
        func = lambda x,y : x/(y+1)
    ))
    all_manip.append(PerfManip(
        name = "l2_pfTop_PFReq_totals",
        counters = [
            "prefetch_send2_pfq",
        ]
    ))
    all_manip.append(PerfManip(
        name = "spp_ptable_perfs",
        counters = [
            "spp_pt_cross_page",
            "spp_pt_lookahead2",
            "spp_pt_bp_nums",
            "spp_pt_nextLine"
        ],
        func = lambda x1,x2,x3,x4 : x1
    ))
    
    
    return all_manip

def get_all_manip(args):
    all_manip = []
    # ipc = PerfManip(
    #     name = "global.IPC",
    #     counters = [f"clock_cycle",
    #     f"commitInstr"],
    #     func = lambda cycle, instr: instr * 1.0 / cycle
    # )
    # all_manip.append(l3cache_mpki_load)
    # all_manip += get_wpu_manip()
    # all_manip += get_rs_manip()
    # all_manip += get_fu_manip()
    if args.pfile:
        all_manip += get_l2_manip_cocotb()
        all_manip += get_prefetch_manip()
    else:
        all_manip += get_base_manip()
        all_manip += get_l2_manip_cocotb()
        all_manip += get_prefetch_manip()
        
    return all_manip