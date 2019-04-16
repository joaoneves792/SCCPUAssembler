#! /usr/bin/env python
import sys
import re
import struct
from ctypes import c_int

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
            self.r[i] = c_int(0)

    def load_byte(self, addr):
        if addr in self.mem:
            return self.mem[addr]
        else:
            self.mem[addr] = 0
            return 0

    def load(self, addr):
        val = c_int((self.load_byte(addr) << 24) | (self.load_byte(addr+1) << 16) |
                (self.load_byte(addr+2) << 8) | (self.load_byte(addr+3)))
        return val
    
    def store(self, addr, x):
        self.mem[addr] = (x.value & 0xff000000) >> 24
        self.mem[addr+1] = (x.value & 0x00ff0000) >> 16
        self.mem[addr+2] = (x.value & 0x0000ff00) >> 8
        self.mem[addr+3] = (x.value & 0x000000ff)


    def set_state(self, x, N, Z, C, V):
        if(N):
            self.N = (1 if x.value < 0 else 0)
        if(Z):
            self.Z = (1 if x.value == 0 else 0)
        if(C):
            self.C = 0 # TODO
        #print(str(hex(value)) + " N" + str(self.N)+ " Z" + str(self.Z)+ " C" + str(self.C)+ " V" + str(self.V))

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
        result = c_int(s.r[self.SA()].value + s.r[self.SB()].value)
        s.set_state(result, True, True, True, True)
        s.r[self.DR()] = result
        if(result.value < s.r[self.SA()].value):
            s.V = 1
    
    def SUB(self, s):
        result = c_int(s.r[self.SA()].value - s.r[self.SB()].value)
        s.set_state(result, True, True, True, True)
        s.r[self.DR()] = result
        if(result.value > s.r[self.SA()].value):
            s.V = 1

    def AND(self, s):
        s.r[self.DR()] = c_int(s.r[self.SA()].value & s.r[self.SB()].value)
        s.set_state(s.r[self.DR()], True, True, False, False)

    def ORRI(self, s):
        s.r[self.DR()] = c_int(s.r[self.SA()].value | self.IMM())
        s.set_state(s.r[self.DR()], True, True, False, False)

    def LSL(self, s):
        result = c_int(s.r[self.SA()].value << self.IMM()) 
        s.set_state(result, True, True, True, False)
        s.r[self.DR()] = result

    def ASR(self, s):
        s.r[self.DR()] = c_int(asr(s.r[self.SA()].value , self.IMM()))
        s.set_state(s.r[self.DR()], True, True, True, True)
        #TODO what is an overflow here?

    def B(self, s):
        s.pc += int(self.args[0][0])

    def BEQ(self, s):
        if s.Z == 1:
            s.pc += int(self.args[0][0])

    def BLT(self, s):
        if s.N != s.V:
            s.pc += int(self.args[0][0])

    def LDR(self, s):
        s.r[self.DR()] = s.load(s.r[self.SA()].value + s.r[self.SB()].value);

    def STR(self, s):
        s.store(s.r[self.SA()].value+s.r[self.SB()].value, s.r[self.DR()])

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
            if(state.r[i].value):
                print("R" + str(i) + " = " + str(hex(state.r[i].value)))

if __name__ == "__main__":
    main()
