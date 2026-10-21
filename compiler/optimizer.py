"""TAC Optimizer for CodeX.

Implements constant folding, constant condition simplification,
and conservative dead-code elimination with detailed transformation logs.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any, Set
from .tac import TacInstruction, TacOp


@dataclass
class OptimizationRecord:
    pass_name: str
    description: str
    original: Optional[str] = None
    replacement: Optional[str] = None
    rule: str = ""
    explanation: str = ""

    def __post_init__(self):
        if not self.explanation:
            self.explanation = self.description
        if not self.description:
            self.description = self.explanation
        if not self.rule:
            if self.pass_name == "Constant Folding":
                self.rule = "CONSTANT_EVALUATION"
            elif self.pass_name == "Branch Simplification":
                self.rule = "DEAD_BRANCH_PRUNING"
            elif self.pass_name == "Dead Code Elimination":
                self.rule = "DEAD_INSTRUCTION_REMOVAL"
            else:
                self.rule = "GENERIC_OPTIMIZATION"


def parse_literal_value(val_str: Optional[str]) -> Tuple[bool, Any]:
    """Attempts to parse a literal string representation back into a Python value."""
    if val_str is None:
        return False, None
    val_str = val_str.strip()
    if val_str == "True":
        return True, True
    if val_str == "False":
        return True, False
    if (val_str.startswith('"') and val_str.endswith('"')) or (val_str.startswith("'") and val_str.endswith("'")):
        return True, val_str[1:-1]
    # Check int
    try:
        if "." not in val_str:
            return True, int(val_str)
    except ValueError:
        pass
    # Check float
    try:
        return True, float(val_str)
    except ValueError:
        pass
    return False, None


def format_literal_value(val: Any) -> str:
    if isinstance(val, bool):
        return "True" if val else "False"
    if isinstance(val, str):
        return repr(val)
    return str(val)


class TacOptimizer:
    def __init__(self):
        self.records: List[OptimizationRecord] = []

    def optimize(self, instructions: List[TacInstruction]) -> Tuple[List[TacInstruction], List[OptimizationRecord]]:
        self.records = []
        current = [self._clone_inst(inst) for inst in instructions]

        # Multi-pass optimization until fixed point or max iterations
        changed = True
        iteration = 0
        max_iterations = 10

        while changed and iteration < max_iterations:
            changed = False
            iteration += 1

            # Pass 1: Constant Folding
            folded_insts, fold_changed = self._pass_constant_folding(current)
            if fold_changed:
                changed = True
                current = folded_insts

            # Pass 2: Branch Simplification on constant conditions
            branch_insts, branch_changed = self._pass_branch_simplification(current)
            if branch_changed:
                changed = True
                current = branch_insts

            # Pass 3: Unreachable Code Elimination (instructions between unconditional jump and next label)
            unreach_insts, unreach_changed = self._pass_unreachable_code_elimination(current)
            if unreach_changed:
                changed = True
                current = unreach_insts

            # Pass 4: Unused Temporary Elimination
            dce_insts, dce_changed = self._pass_unused_temporary_elimination(current)
            if dce_changed:
                changed = True
                current = dce_insts

        return current, self.records

    def _clone_inst(self, inst: TacInstruction) -> TacInstruction:
        return TacInstruction(
            op=inst.op,
            dest=inst.dest,
            arg1=inst.arg1,
            arg2=inst.arg2,
            operator=inst.operator,
            args=list(inst.args),
            comment=inst.comment,
            line=inst.line,
        )

    def _pass_constant_folding(self, instructions: List[TacInstruction]) -> Tuple[List[TacInstruction], bool]:
        new_instructions: List[TacInstruction] = []
        changed = False

        # Track known values of temporaries: dest -> literal string
        known_constants: Dict[str, str] = {}

        for inst in instructions:
            # Propagate known constants to instruction operands
            if inst.arg1 in known_constants:
                inst.arg1 = known_constants[inst.arg1]
            if inst.arg2 in known_constants:
                inst.arg2 = known_constants[inst.arg2]
            if inst.op == TacOp.PRINT:
                inst.args = [known_constants.get(a, a) for a in inst.args]

            # Labels or jumps invalidate straightforward constant propagation across blocks for simplicity & safety
            if inst.op in (TacOp.LABEL, TacOp.JUMP, TacOp.JUMP_IF_FALSE, TacOp.JUMP_IF_TRUE):
                known_constants.clear()
                new_instructions.append(inst)
                continue

            arg1 = inst.arg1
            arg2 = inst.arg2

            if inst.op == TacOp.BINARY:
                is_lit1, val1 = parse_literal_value(arg1)
                is_lit2, val2 = parse_literal_value(arg2)
                op = inst.operator

                if is_lit1 and is_lit2:
                    computed = None
                    valid = False
                    try:
                        if op == "+":
                            computed = val1 + val2
                            valid = True
                        elif op == "-":
                            computed = val1 - val2
                            valid = True
                        elif op == "*":
                            computed = val1 * val2
                            valid = True
                        elif op == "/" and val2 != 0:
                            computed = val1 / val2
                            valid = True
                        elif op == "//" and val2 != 0:
                            computed = val1 // val2
                            valid = True
                        elif op == "%" and val2 != 0:
                            computed = val1 % val2
                            valid = True
                        elif op == "==":
                            computed = val1 == val2
                            valid = True
                        elif op == "!=":
                            computed = val1 != val2
                            valid = True
                        elif op == "<":
                            computed = val1 < val2
                            valid = True
                        elif op == "<=":
                            computed = val1 <= val2
                            valid = True
                        elif op == ">":
                            computed = val1 > val2
                            valid = True
                        elif op == ">=":
                            computed = val1 >= val2
                            valid = True
                        elif op == "and":
                            computed = bool(val1 and val2)
                            valid = True
                        elif op == "or":
                            computed = bool(val1 or val2)
                            valid = True
                    except Exception:
                        valid = False

                    if valid and computed is not None:
                        val_str = format_literal_value(computed)
                        orig_str = inst.to_code_str().strip()
                        new_inst = TacInstruction(
                            op=TacOp.ASSIGN,
                            dest=inst.dest,
                            arg1=val_str,
                            line=inst.line,
                        )
                        new_instructions.append(new_inst)
                        if inst.dest:
                            known_constants[inst.dest] = val_str
                        self.records.append(
                            OptimizationRecord(
                                pass_name="Constant Folding",
                                rule="CONSTANT_FOLD_BINARY",
                                description=f"Folded constant expression '{arg1} {op} {arg2}' -> {val_str}",
                                original=orig_str,
                                replacement=new_inst.to_code_str().strip(),
                                explanation=f"Evaluated binary operation ({arg1} {op} {arg2}) statically at compile time, eliminating runtime arithmetic overhead.",
                            )
                        )
                        changed = True
                        continue

            elif inst.op == TacOp.UNARY:
                is_lit, val = parse_literal_value(arg1)
                op = inst.operator
                if is_lit:
                    computed = None
                    valid = False
                    try:
                        if op == "+":
                            computed = +val
                            valid = True
                        elif op == "-":
                            computed = -val
                            valid = True
                        elif op == "not":
                            computed = not val
                            valid = True
                    except Exception:
                        valid = False

                    if valid and computed is not None:
                        val_str = format_literal_value(computed)
                        orig_str = inst.to_code_str().strip()
                        new_inst = TacInstruction(
                            op=TacOp.ASSIGN,
                            dest=inst.dest,
                            arg1=val_str,
                            line=inst.line,
                        )
                        new_instructions.append(new_inst)
                        if inst.dest:
                            known_constants[inst.dest] = val_str
                        self.records.append(
                            OptimizationRecord(
                                pass_name="Constant Folding",
                                rule="CONSTANT_FOLD_UNARY",
                                description=f"Folded constant unary expression '{op} {arg1}' -> {val_str}",
                                original=orig_str,
                                replacement=new_inst.to_code_str().strip(),
                                explanation=f"Evaluated unary operation ({op} {arg1}) statically at compile time, replacing expression with literal {val_str}.",
                            )
                        )
                        changed = True
                        continue

            elif inst.op == TacOp.ASSIGN:
                is_lit, _ = parse_literal_value(arg1)
                if is_lit and inst.dest:
                    known_constants[inst.dest] = arg1
                inst.arg1 = arg1

            new_instructions.append(inst)

        return new_instructions, changed

    def _pass_branch_simplification(self, instructions: List[TacInstruction]) -> Tuple[List[TacInstruction], bool]:
        new_instructions: List[TacInstruction] = []
        changed = False

        for inst in instructions:
            if inst.op == TacOp.JUMP_IF_FALSE:
                is_lit, val = parse_literal_value(inst.arg1)
                if is_lit:
                    bool_val = bool(val)
                    orig_str = inst.to_code_str().strip()
                    if bool_val is False:
                        # Condition is always False -> always jump!
                        new_inst = TacInstruction(op=TacOp.JUMP, arg1=inst.arg2, line=inst.line)
                        new_instructions.append(new_inst)
                        self.records.append(
                            OptimizationRecord(
                                pass_name="Branch Simplification",
                                rule="BRANCH_SIMPLIFY_TAKEN",
                                description=f"Simplified 'if_false False goto {inst.arg2}' to unconditional jump",
                                original=orig_str,
                                replacement=new_inst.to_code_str().strip(),
                                explanation=f"Branch condition evaluated to static False; 'if_false' is guaranteed to branch, converted to direct 'goto {inst.arg2}'.",
                            )
                        )
                        changed = True
                        continue
                    else:
                        # Condition is always True -> never jump, discard instruction!
                        self.records.append(
                            OptimizationRecord(
                                pass_name="Branch Simplification",
                                rule="DEAD_BRANCH_REMOVAL",
                                description=f"Removed dead branch 'if_false True goto {inst.arg2}'",
                                original=orig_str,
                                replacement="(eliminated)",
                                explanation=f"Branch condition evaluated to static True; 'if_false' will never branch to {inst.arg2}. Dead conditional jump instruction removed.",
                            )
                        )
                        changed = True
                        continue

            elif inst.op == TacOp.JUMP_IF_TRUE:
                is_lit, val = parse_literal_value(inst.arg1)
                if is_lit:
                    bool_val = bool(val)
                    orig_str = inst.to_code_str().strip()
                    if bool_val is True:
                        new_inst = TacInstruction(op=TacOp.JUMP, arg1=inst.arg2, line=inst.line)
                        new_instructions.append(new_inst)
                        self.records.append(
                            OptimizationRecord(
                                pass_name="Branch Simplification",
                                rule="BRANCH_SIMPLIFY_TAKEN",
                                description=f"Simplified 'if_true True goto {inst.arg2}' to unconditional jump",
                                original=orig_str,
                                replacement=new_inst.to_code_str().strip(),
                                explanation=f"Branch condition evaluated to static True; 'if_true' is guaranteed to branch, converted to direct 'goto {inst.arg2}'.",
                            )
                        )
                        changed = True
                        continue
                    else:
                        self.records.append(
                            OptimizationRecord(
                                pass_name="Branch Simplification",
                                rule="DEAD_BRANCH_REMOVAL",
                                description=f"Removed dead branch 'if_true False goto {inst.arg2}'",
                                original=orig_str,
                                replacement="(eliminated)",
                                explanation=f"Branch condition evaluated to static False; 'if_true' will never branch to {inst.arg2}. Dead conditional jump instruction removed.",
                            )
                        )
                        changed = True
                        continue

            new_instructions.append(inst)

        return new_instructions, changed

    def _pass_unreachable_code_elimination(self, instructions: List[TacInstruction]) -> Tuple[List[TacInstruction], bool]:
        new_instructions: List[TacInstruction] = []
        changed = False
        is_unreachable = False

        for inst in instructions:
            if inst.op == TacOp.LABEL:
                is_unreachable = False
                new_instructions.append(inst)
                continue

            if is_unreachable:
                # Discard instruction
                self.records.append(
                    OptimizationRecord(
                        pass_name="Dead Code Elimination",
                        rule="UNREACHABLE_CODE_ELIMINATION",
                        description=f"Eliminated unreachable instruction following unconditional jump",
                        original=inst.to_code_str().strip(),
                        replacement="(eliminated)",
                        explanation="Instruction succeeds an unconditional jump prior to the next landing label. Control flow cannot enter this location, instruction removed.",
                    )
                )
                changed = True
                continue

            new_instructions.append(inst)

            if inst.op == TacOp.JUMP:
                is_unreachable = True

        return new_instructions, changed

    def _pass_unused_temporary_elimination(self, instructions: List[TacInstruction]) -> Tuple[List[TacInstruction], bool]:
        # Collect all used variables/temporaries across instructions
        used_symbols: Set[str] = set()

        for inst in instructions:
            if inst.op == TacOp.PRINT:
                used_symbols.update(inst.args)
            elif inst.op in (TacOp.JUMP_IF_FALSE, TacOp.JUMP_IF_TRUE):
                if inst.arg1:
                    used_symbols.add(inst.arg1)
            elif inst.op in (TacOp.BINARY, TacOp.UNARY, TacOp.ASSIGN):
                if inst.arg1:
                    used_symbols.add(inst.arg1)
                if inst.arg2:
                    used_symbols.add(inst.arg2)

        new_instructions: List[TacInstruction] = []
        changed = False

        for inst in instructions:
            # Check if inst defines a temporary variable (starts with 't' followed by digits)
            if inst.dest and inst.dest.startswith("t") and inst.dest[1:].isdigit():
                if inst.dest not in used_symbols:
                    self.records.append(
                        OptimizationRecord(
                            pass_name="Dead Code Elimination",
                            rule="UNUSED_TEMPORARY_ELIMINATION",
                            description=f"Eliminated unused temporary assignment '{inst.dest}'",
                            original=inst.to_code_str().strip(),
                            replacement="(eliminated)",
                            explanation=f"Temporary variable '{inst.dest}' is defined but never referenced by any subsequent instruction. Assignment removed without observable side effects.",
                        )
                    )
                    changed = True
                    continue

            new_instructions.append(inst)

        return new_instructions, changed


def optimize_tac(instructions: List[TacInstruction]) -> Tuple[List[TacInstruction], List[OptimizationRecord]]:
    optimizer = TacOptimizer()
    return optimizer.optimize(instructions)
