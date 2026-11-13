#!/usr/bin/env python3
class VM:
    def __init__(self, registers: list[int], memory: list[int]):
        self.halted_addr: int | None = None
        self.pc: int = 0
        self.reg: list[int] = registers
        self.mem: list[int] = memory + [0] * 10

    def step(self):
        # br = self.pc == 0x32 or self.pc > 0x83
        br = False
        if br:
            instrs = ['halt', 'movi', 'movr', 'ldr', 'str', 'add', 'mul', 'not', 'and', 'or', 'xor', 'shl', 'shr', 'jmp', 'jeq']
            print(f'{hex(self.pc)}: {instrs[self.mem[self.pc]]}', flush=True)
            print(f'[{', '.join(hex(r) for r in self.reg)}]', flush=True)
        match self.mem[self.pc]:
            # 0x0 halt Reg0
            case 0x0: 
                reg0_index   = self.mem[self.pc + 1]
                reg0_content = self.reg[reg0_index]
                self.halted_addr = reg0_content

            # 0x1 movi Reg0, #Imm
            case 0x1:
                reg0_index = self.mem[self.pc + 1]
                immediate  = self.mem[self.pc + 2]
                self.reg[reg0_index] = immediate
                self.pc += 3

            # 0x2 movr Reg0, Reg1
            case 0x2:
                reg0_index   = self.mem[self.pc + 1]
                reg1_index   = self.mem[self.pc + 2]
                reg1_content = self.reg[reg1_index]
                self.reg[reg0_index] = reg1_content
                self.pc += 3

            # 0x3 ldr Reg0, Reg1
            case 0x3:
                reg0_index   = self.mem[self.pc + 1]
                reg1_index   = self.mem[self.pc + 2]
                reg1_content = self.reg[reg1_index]
                mem_content  = self.mem[reg1_content]
                self.reg[reg0_index] = mem_content
                self.pc += 3

            # 0x4 str Reg0 Reg1
            case 0x4:
                reg0_index   = self.mem[self.pc + 1]
                reg0_content = self.reg[reg0_index]
                reg1_index   = self.mem[self.pc + 2]
                reg1_content = self.reg[reg1_index]
                self.mem[reg1_content] = reg0_content
                self.pc += 3
                
            # 0x5 add Reg0 Reg1 Reg2
            case 0x5:
                reg0_index   = self.mem[self.pc + 1]
                reg1_index   = self.mem[self.pc + 2]
                reg1_content = self.reg[reg1_index]
                reg2_index   = self.mem[self.pc + 3]
                reg2_content = self.reg[reg2_index]
                self.reg[reg0_index] = reg1_content + reg2_content
                self.pc += 4

            # 0x6 mul Reg0 Reg1 Reg2
            case 0x6:
                reg0_index   = self.mem[self.pc + 1]
                reg1_index   = self.mem[self.pc + 2]
                reg1_content = self.reg[reg1_index]
                reg2_index   = self.mem[self.pc + 3]
                reg2_content = self.reg[reg2_index]
                self.reg[reg0_index] = reg1_content * reg2_content
                self.pc += 4

            # 0x7 not Reg0 Reg1
            case 0x7:
                reg0_index   = self.mem[self.pc + 1]
                reg1_index   = self.mem[self.pc + 2]
                reg1_content = self.reg[reg1_index]
                self.reg[reg0_index] = reg1_content ^ (2**reg1_content.bit_length() - 1)
                self.pc += 3

            # 0x8 and Reg0 Reg1 Reg2
            case 0x8:
                reg0_index   = self.mem[self.pc + 1]
                reg1_index   = self.mem[self.pc + 2]
                reg1_content = self.reg[reg1_index]
                reg2_index   = self.mem[self.pc + 3]
                reg2_content = self.reg[reg2_index]
                self.reg[reg0_index] = reg1_content & reg2_content
                self.pc += 4

            # 0x9 or  Reg0 Reg1 Reg2
            case 0x9:
                reg0_index   = self.mem[self.pc + 1]
                reg1_index   = self.mem[self.pc + 2]
                reg1_content = self.reg[reg1_index]
                reg2_index   = self.mem[self.pc + 3]
                reg2_content = self.reg[reg2_index]
                self.reg[reg0_index] = reg1_content | reg2_content
                self.pc += 4

            # 0xa xor Reg0 Reg1 Reg2
            case 0xa:
                reg0_index   = self.mem[self.pc + 1]
                reg1_index   = self.mem[self.pc + 2]
                reg1_content = self.reg[reg1_index]
                reg2_index   = self.mem[self.pc + 3]
                reg2_content = self.reg[reg2_index]
                self.reg[reg0_index] = reg1_content ^ reg2_content
                self.pc += 4

            # 0xb shl Reg0 Reg1 Reg2
            case 0xb:
                reg0_index   = self.mem[self.pc + 1]
                reg1_index   = self.mem[self.pc + 2]
                reg1_content = self.reg[reg1_index]
                reg2_index   = self.mem[self.pc + 3]
                reg2_content = self.reg[reg2_index]
                self.reg[reg0_index] = reg1_content << reg2_content
                self.pc += 4

            # 0xc shr Reg0 Reg1 Reg2
            case 0xc:
                reg0_index   = self.mem[self.pc + 1]
                reg1_index   = self.mem[self.pc + 2]
                reg1_content = self.reg[reg1_index]
                reg2_index   = self.mem[self.pc + 3]
                reg2_content = self.reg[reg2_index]
                self.reg[reg0_index] = reg1_content >> reg2_content
                self.pc += 4

            # 0xd jmp Reg0
            case 0xd:
                reg0_index   = self.mem[self.pc + 1]
                reg0_content = self.reg[reg0_index]
                self.pc = reg0_content

            # 0xe jeq  Reg0 Reg1 Reg2
            case 0xe:
                reg0_index   = self.mem[self.pc + 1]
                reg0_content = self.reg[reg0_index]
                reg1_index   = self.mem[self.pc + 2]
                reg1_content = self.reg[reg1_index]
                reg2_index   = self.mem[self.pc + 3]
                reg2_content = self.reg[reg2_index]
                self.pc = reg2_content if reg0_content == reg1_content else self.pc + 4

            case int(n): raise Exception(f"Bad Instruction: {n}")

        if br:
            print(f'[{', '.join(hex(r) for r in self.reg)}]', flush=True)
            input()

    def step_until_halt(self):
        while self.halted_addr is None:
            self.step()

        out_str = ''
        while (c := self.mem[self.halted_addr]) != 0:
            out_str += chr(c)
            self.halted_addr += 1

        return out_str

def parse_bytes(filename: str) -> tuple[list[int], list[int]]:
    with open(filename, 'r') as f:
        registers = [0] * 6
        memory = [int(n) for n in f.read().split(';')]
        registers[4] = len(memory)
        registers[5] = len(memory)
        
        return registers, memory

if __name__ == '__main__':
    import argparse
    ascii_art = (
r"""
       _
       \`*-.
        )  _`-.
       .  : `. .
       : _   '  \
       ; *` _.   `*-._
       `-.-'          `-.
         ;       `       `.
         :.       .        \
         . \  .   :   .-'   .
         '  `+.;  ;  '      :
         :  '  |    ;       ;-.
         ; '   : :`-:     _.`* ;
[bug] .*' /  .*' ; .*`- +'  `*'
      `*-*   `*-*  `*-*'
"""
)
    parser = argparse.ArgumentParser(
        prog="BAVM",
        description="Grace's Awesome Virtual Machine\n"+ascii_art,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('filename', help="Path to intcode")
    args = parser.parse_args()

    registers, memory = parse_bytes(args.filename)
    vm = VM(registers, memory)
    print(vm.step_until_halt())


