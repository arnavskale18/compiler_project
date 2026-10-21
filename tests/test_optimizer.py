import pytest
from compiler.pipeline import compile_source
from compiler.tac import TacInstruction, TacOp
from compiler.optimizer import optimize_tac


def test_optimizer_constant_folding_arithmetic():
    src = "x = 10 + 5 * 2\n"
    res = compile_source(src)
    assert res.success is True

    # Check original TAC had binary operations
    assert any(i.op == TacOp.BINARY for i in res.tac)

    # Check that in optimized TAC, x is assigned folded constant 20
    assigns = [i for i in res.optimized_tac if i.op == TacOp.ASSIGN and i.dest == "x"]
    assert len(assigns) == 1
    assert assigns[0].arg1 == "20"

    # Check optimization records recorded constant folding
    fold_records = [r for r in res.optimization_log if r.pass_name == "Constant Folding"]
    assert len(fold_records) > 0


def test_optimizer_branch_simplification():
    # if True branch should simplify
    src = (
        "if 10 > 5:\n"
        "    x = 1\n"
        "else:\n"
        "    x = 2\n"
    )
    res = compile_source(src)
    assert res.success is True

    records = [r for r in res.optimization_log if r.pass_name in ("Branch Simplification", "Dead Code Elimination")]
    assert len(records) > 0


def test_optimizer_dead_code_elimination_unused_temps():
    # Direct instruction test
    insts = [
        TacInstruction(op=TacOp.ASSIGN, dest="t0", arg1="100"),
        TacInstruction(op=TacOp.ASSIGN, dest="x", arg1="50"),
        TacInstruction(op=TacOp.PRINT, args=["x"]),
    ]
    opt_insts, log = optimize_tac(insts)
    # t0 is never used, so it should be eliminated
    dests = [i.dest for i in opt_insts]
    assert "t0" not in dests
    assert "x" in dests


def test_optimizer_levels_o0_to_o3():
    from compiler.optimizer import TacOptimizer

    # Test -O0: No optimization, empty record log
    opt0 = TacOptimizer(optimization_level=0)
    insts = [
        TacInstruction(op=TacOp.ASSIGN, dest="t0", arg1="100"),
        TacInstruction(op=TacOp.BINARY, dest="t1", arg1="2", operator="+", arg2="3"),
    ]
    res_insts, records = opt0.optimize(insts)
    assert len(records) == 0
    assert len(res_insts) == 2
    assert res_insts[1].op == TacOp.BINARY

    # Test -O1: Constant folding only, unused temps remain
    opt1 = TacOptimizer(level=1)
    res_insts1, records1 = opt1.optimize(insts)
    assert len(records1) > 0
    # t1 should be folded to 5, but t0 should NOT be eliminated in O1
    dests1 = [i.dest for i in res_insts1]
    assert "t0" in dests1
    assert "t1" in dests1

    # Test -O2: Unused temporary elimination included
    opt2 = TacOptimizer(optimization_level=2)
    insts2 = [
        TacInstruction(op=TacOp.ASSIGN, dest="t0", arg1="100"),
        TacInstruction(op=TacOp.ASSIGN, dest="x", arg1="50"),
        TacInstruction(op=TacOp.PRINT, args=["x"]),
    ]
    res_insts2, records2 = opt2.optimize(insts2)
    dests2 = [i.dest for i in res_insts2]
    assert "t0" not in dests2
    assert "x" in dests2

    # Test -O3: Multi-pass fixed-point
    opt3 = TacOptimizer(optimization_level=3)
    res_insts3, records3 = opt3.optimize(insts2)
    dests3 = [i.dest for i in res_insts3]
    assert "t0" not in dests3


def test_pipeline_configurable_opt_levels():
    src = "x = 10 + 5 * 2\nprint(x)\n"
    # -O0 should have 0 records and BINARY op
    r0 = compile_source(src, opt_level=0)
    assert r0.success is True
    assert r0.opt_level == 0
    assert len(r0.optimization_log) == 0

    # -O2 should fold constants
    r2 = compile_source(src, opt_level=2)
    assert r2.success is True
    assert r2.opt_level == 2
    assert len(r2.optimization_log) > 0

