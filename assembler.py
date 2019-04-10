#! /usr/bin/env python
import sys
import re
import struct

def bindigits(n, bits):
    s = bin(n & int("1"*bits, 2))[2:]
    return ("{0:0>%s}" % (bits)).format(s)

class Instruction:
    OPCODE = {
            'NOP' : ("000000", re.compile(r'()()$'), (26,)),
            'ADD' : ("010000", re.compile(r'R(\d+),R(\d+),R(\d+)$'), (5, 5, 5)),
            'SUB' : ("010001", re.compile(r'R(\d+),R(\d+),R(\d+)$'), (5, 5, 5)),
            'AND' : ("010010", re.compile(r'R(\d+),R(\d+),R(\d+)$'), (5, 5, 5)),
            'ORRI': ("110011", re.compile(r'R(\d+),R(\d+),#([-\+]?\d+)$'), (5, 5, 16)),
            'LSL' : ("101101", re.compile(r'R(\d+),R(\d+),#(\d+)$'), (5, 5, 16)),
            'ASR' : ("101111", re.compile(r'R(\d+),R(\d+),#(\d+)$'), (5, 5, 16)),
            'B'   : ("100000", re.compile(r'([-\+]?\d+)()$'), (26,)),
            'B.EQ': ("100001", re.compile(r'([-\+]?\d+)()$'), (26,)),
            'B.LT': ("100011", re.compile(r'([-\+]?\d+)()$'), (26,)),
            'LDR' : ("011100", re.compile(r'R(\d+),\[R(\d+)[\+|,]R(\d+)\]$'), (5, 5, 5)),
            'STR' : ("011101", re.compile(r'R(\d+),\[R(\d+)[\+|,]R(\d+)\]$'), (5, 5, 5)),
            }

    def __init__(self, source_line):
        self.source = source_line.upper().strip().split()
        self.op = self.source[0]
        self.opcode = Instruction.OPCODE[self.op]
        self.source_args = "".join(self.source[1:])
        self.args = self.opcode[1].findall(self.source_args)


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

def main():
    source_path = sys.argv[1]
    source = []
    with open(source_path) as f:
        source = f.readlines()
    
    for i, line in enumerate(source):
        instr = Instruction(line)
        print("\t-- " + instr.get_source_instr())
        print("\t" + str(i) + " => " + instr.get_binary_instr() + ",")


if __name__ == "__main__":
    main()
