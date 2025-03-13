
"""
Val Levy
02-19-2025

Credits:
    ChatGPT: refining methods.
"""

import context  #  Python import search from project root
from instruction_set.instr_format import Instruction, OpCode, CondFlag, decode

from cpu.memory import Memory
from cpu.register import Register, ZeroRegister
from cpu.mvc import MVCEvent, MVCListenable

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

class ALU(object):
    """The arithmetic logic unit (also called a "functional unit"
    in a modern CPU) executes a selected function but does not
    otherwise manage CPU state. A modern CPU core may have several
    ALUs to boost performance by performing multiple operatons
    in parallel, but the Duck Machine has just one ALU in one core.
    """
    # The ALU chooses one operation to apply based on a provided
    # operation code.  These are just simple functions of two arguments;
    # in hardware we would use a multiplexer circuit to connect the
    # inputs and output to the selected circuitry for each operation.
    ALU_OPS = {
        OpCode.ADD: lambda x, y: x + y,
        OpCode.SUB: lambda x, y: x - y,
        OpCode.MUL: lambda x, y: x * y,
        OpCode.DIV: lambda x, y: x // y,
        # For memory access operations load, store, the ALU
        # performs the address calculation
        OpCode.LOAD: lambda x, y: x + y,
        OpCode.STORE: lambda x, y: x + y,
        # Some operations perform no operation
        OpCode.HALT: lambda x, y: 0
    }

    def exec(self, op: OpCode, in1: int, in2: int) -> tuple[int, CondFlag]:
        """Execute an operation and return the result and condition flags."""
        try:
            result = self.ALU_OPS[op](in1, in2)
        except Exception as e:
            return 0, CondFlag.V

        if result == 0:
            flag = CondFlag.Z
        elif result < 0:
            flag = CondFlag.M
        else:
            flag = CondFlag.P

        return result, flag

class CPUStep(MVCEvent):
    """CPU is beginning step with PC at a given address"""
    def __init__(self, subject: "CPU", pc_addr: int,
                 instr_word: int, instr: Instruction)-> None:
        self.subject = subject
        self.pc_addr = pc_addr
        self.instr_word = instr_word
        self.instr = instr

class CPU(MVCListenable):
    """Duck Machine central processing unit (CPU)
    has 16 registers (including r0 that always holds zero
    and r15 that holds the program counter), a few
    flag registers (condition codes, halted state),
    and some logic for sequencing execution.  The CPU
    does not contain the main memory but has a bus connecting
    it to a separate memory.
    """
    def __init__(self, memory: Memory):
        super().__init__()
        self.memory = memory  # Not part of CPU; what we really have is a connection
        self.registers = [ ZeroRegister(), Register(), Register(), Register(),
                           Register(), Register(), Register(), Register(),
                           Register(), Register(), Register(), Register(),
                           Register(), Register(), Register(), Register() ]
        self.condition = CondFlag.ALWAYS
        self.halted = False
        self.alu = ALU()

    def step(self):
        """One fetch/decode/execute step"""
        # Fetch
        instr_addr = self.registers[15].get()
        instr_word = self.memory.get(instr_addr)

        # Decode
        instr = decode(instr_word)
        self.notify_all(CPUStep(self, instr_addr, instr_word, instr))

        # Execute
        # Assuming instr is the decoded instruction and self.condition is satisfied
        if instr.op in [OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV]:
            operand1 = self.registers[instr.reg_src1].get()
            operand2 = self.registers[instr.reg_src2].get() + instr.offset
            result, new_condition = self.alu.exec(instr.op, operand1, operand2)
            self.registers[instr.reg_target].put(result)
            self.condition = new_condition
        elif instr.op == OpCode.LOAD:
            effective_address = self.registers[instr.reg_src2].get() + instr.offset
            value = self.memory.get(effective_address)
            self.registers[instr.reg_target].put(value)
        elif instr.op == OpCode.STORE:
            effective_address = self.registers[instr.reg_src2].get() + instr.offset
            value = self.registers[instr.reg_target].get()
            self.memory.put(effective_address, value)
        elif instr.op == OpCode.HALT:
            self.halted = True
        else:
            self.registers[15].put(self.registers[15].get() + 1)

    def run(self, from_addr=0,  single_step=False) -> None:
        """Step the CPU until it executes a HALT"""
        self.halted = False
        self.registers[15].put(from_addr)
        step_count = 0
        while not self.halted:
            if single_step:
                input(f"Step {step_count}; press enter")
            self.step()
            step_count += 1
