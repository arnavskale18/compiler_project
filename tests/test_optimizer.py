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
