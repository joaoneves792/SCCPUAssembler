#! /usr/bin/env python
import sys
import re
import struct

def bindigits(n, bits):
    s = bin(n & int("1"*bits, 2))[2:]
    return ("{0:0>%s}" % (bits)).format(s)

def asr(num, shift):
    return ((num >> shift) | (0xffffffff << 32-shift)) & (0xffffffff)

class EmulationState:
    def __init__(self):
        self.instruction_memory = []
        self.pc = 0
        self.r = {}
        self.mem = {}
        self.N = 0
        self.Z = 0
        self.C = 0
        self.V = 0
        for i in range(32):
            self.r[i] = 0

    #TODO fix for byte addressing
    def load(self, addr):
        if addr in self.mem:
            return self.mem[addr]
        else:
            self.mem[addr] = 0
            return self.load(addr)
    
    def store(self, addr, value):
        self.mem[addr] = value

    def set_state(self, value, N, Z, C, V):
        if(N):
            self.N = (1 if value < 0 else 0)
        if(Z):
            self.Z = (1 if value == 0 else 0)
        if(C):
            self.C = 0 # TODO
        if(V):
            self.V = (1 if value > 0xffffffff else 0)
        #print(str(hex(value)) + " N" + str(self.N)+ " Z" + str(self.Z)+ " C" + str(self.C)+ " V" + str(self.V))

class UALInstruction:
    OPCODE = {
            'NOP' : ("orr\tr0, r0, r0",),
            'ADD' : ("adds\tr{0}, r{1}, r{2}",),
            'SUB' : ("subs\tr{0}, r{1}, r{2}",),
            'AND' : ("ands\tr{0}, r{1}, r{2}",),
            'ORRI': ("sub\tsp, sp, #8", "str\tr0, [sp, #0]", "ldr\tr0, ={2}", "orr\tr{0}, r{1}, r0", "str\tr{0}, [sp, #4]", "ldr\tr0, [sp, #0]", "ldr\tr{0}, [sp, #4]", "add\t sp, sp, #8", "orrs\tr{0}, r{0}, r{0}"),
            'LSL' : ("movs\tr{0}, r{1}, lsl #{2}",),
            'ASR' : ("movs\tr{0}, r{1}, asr #{2}",),
            'LDR' : ("ldr\tr{0}, [r{1}, r{2}]",),
            'STR' : ("str\tr{0}, [r{1}, r{2}]",),
            }
    BRANCHES = {       
            'B'   : ("b\t{0}",),
            'B.EQ': ("beq\t{0}",),
            'B.LT': ("blt\t{0}",),
            }

    def __init__(self, instruction):
        self.SCop = instruction  # type: Instruction
        self.ual = []
        self.label = "\t"
        if self.SCop.op in UALInstruction.OPCODE:
            ual = UALInstruction.OPCODE[self.SCop.op]
            for instr in ual:
                self.ual.append(instr.format(*self.SCop.args[0]) + "\n")
        elif self.SCop.op in UALInstruction.BRANCHES:
            self.ual.append("branches not implemented\n")
    
    def get_ual(self):
        code = ""
        code += self.label + "\t"
        code += self.ual[0]
        for line in self.ual[1:]:
            code += "\t\t"
            code += line
        return code


class Instruction:
    def __init__(self, source_line):
        self.source = source_line.upper().strip().split()
        self.op = self.source[0]
        self.opcode = Instruction.OPCODE[self.op]
        self.source_args = "".join(self.source[1:])
        self.args = self.opcode[1].findall(self.source_args)

    def NOP(self, s):
        pass

    def ADD(self, s):
        result = s.r[self.SA()] + s.r[self.SB()]
        s.set_state(result, True, True, True, True)
        s.r[self.DR()] = result & 0xffffffff
    
    def SUB(self, s):
        result = s.r[self.SA()] - s.r[self.SB()]
        s.set_state(result, True, True, True, True)
        s.r[self.DR()] = result & 0xffffffff

    def AND(self, s):
        s.r[self.DR()] = s.r[self.SA()] & s.r[self.SB()]
        s.set_state(s.r[self.DR()], True, True, False, False)

    def ORRI(self, s):
        s.r[self.DR()] = s.r[self.SA()] | self.IMM()
        s.set_state(s.r[self.DR()], True, True, False, False)

    def LSL(self, s):
        result = (s.r[self.SA()] << self.IMM()) 
        s.set_state(result, True, True, True, False)
        s.r[self.DR()] = result & 0xffffffff

    def ASR(self, s):
        s.r[self.DR()] = asr(s.r[self.SA()], self.IMM())
        s.set_state(s.r[self.DR()], True, True, True, True)

    def B(self, s):
        s.pc += int(self.args[0][0])

    def BEQ(self, s):
        if s.Z == 1:
            s.pc += int(self.args[0][0])

    def BLT(self, s):
        if s.N != s.V:
            s.pc += int(self.args[0][0])

    def LDR(self, s):
        s.r[self.DR()] = s.load(s.r[self.SA()] + s.r[self.SB()]);

    def STR(self, s):
        s.store(s.r[self.SA()]+s.r[self.SB()], s.r[self.DR()])

    def DR(self):
        return int(self.args[0][0])

    def SA(self):
        return int(self.args[0][1])
    
    def SB(self):
        return int(self.args[0][2])
    
    def IMM(self):
        return int(self.args[0][2])

    OPCODE = {
            'NOP' : ("000000", re.compile(r'()()$'), (26,), NOP),
            'ADD' : ("010000", re.compile(r'R(\d+),R(\d+),R(\d+)$'), (5, 5, 5), ADD),
            'SUB' : ("010001", re.compile(r'R(\d+),R(\d+),R(\d+)$'), (5, 5, 5), SUB),
            'AND' : ("010010", re.compile(r'R(\d+),R(\d+),R(\d+)$'), (5, 5, 5), AND),
            'ORRI': ("110011", re.compile(r'R(\d+),R(\d+),#([-\+]?\d+)$'), (5, 5, 16), ORRI),
            'LSL' : ("101101", re.compile(r'R(\d+),R(\d+),#(\d+)$'), (5, 5, 16), LSL),
            'ASR' : ("101111", re.compile(r'R(\d+),R(\d+),#(\d+)$'), (5, 5, 16), ASR),
            'B'   : ("100000", re.compile(r'([-\+]?\d+)()$'), (26,), B),
            'B.EQ': ("100001", re.compile(r'([-\+]?\d+)()$'), (26,), BEQ),
            'B.LT': ("100011", re.compile(r'([-\+]?\d+)()$'), (26,), BLT),
            'LDR' : ("011100", re.compile(r'R(\d+),\[R(\d+)[\+|,]R(\d+)\]$'), (5, 5, 5), LDR),
            'STR' : ("011101", re.compile(r'R(\d+),\[R(\d+)[\+|,]R(\d+)\]$'), (5, 5, 5), STR),
            }
    
    def get_binary_instr(self):
        string = "\"" + self.opcode[0] + "\""

        length = 6  # 6 is opcode size
        for i, arg in enumerate(self.args[0]):
            if len(arg) == 0:
                break
            arg_len = self.opcode[2][i]
            length += arg_len
            string += " & \""
            string += bindigits(int(arg), arg_len)
            string += "\""

        if length < 32:
            string += " & \"" + format(0, "0>"+str(32-length)+"b") + "\""   
        return string
    
    def get_source_instr(self):
        return self.op + " " + "".join(self.source[1:])

    def execute(self, state):
        self.opcode[3](self, state)
        print(state.r[0])

def main():
    source_path = sys.argv[1]
    source = []
    with open(source_path) as f:
        source = f.readlines()
   
    if len(sys.argv) < 3:
        for i, line in enumerate(source):
            instr = Instruction(line)
            print("\t-- " + instr.get_source_instr())
            print("\t" + str(i) + " => " + instr.get_binary_instr() + ",")
        return
    else:
        state = EmulationState()
        for i, line in enumerate(source):
            instr = Instruction(line)
            state.instruction_memory.append(instr)
        while(state.pc < len(state.instruction_memory)):
            state.instruction_memory[state.pc].execute(state)
            state.pc += 1
        for i in state.r:
            print("R" + str(i) + " = " + str(hex(state.r[i])))
        for i in state.mem:
            print(str(hex(i)) + " = " + str(hex(state.mem[i])))

if __name__ == "__main__":
    main()
