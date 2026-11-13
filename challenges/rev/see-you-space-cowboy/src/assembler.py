#!/usr/bin/env python3
import re
import enum
import abc
import dataclasses


class Operand(enum.StrEnum):
    Reg = 'register'
    Imm = 'immediate'

class Instruction(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def mnemonic() -> str: ...

    @staticmethod
    @abc.abstractmethod
    def operands() -> tuple[Operand, ...]: ...

    @staticmethod
    @abc.abstractmethod
    def opcode() -> int: ...

    def __len__(self) -> int: return len(self.operands()) + 1

@dataclasses.dataclass()
class Halt(Instruction):
    reg_0: int
    @staticmethod
    def mnemonic() -> str: return 'halt'

    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg,)

    @staticmethod
    def opcode() -> int: return 0x0


@dataclasses.dataclass()
class MovImm(Instruction):
    reg_0: int
    imm: int | str
    @staticmethod
    def mnemonic() -> str: return 'movi'

    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg, Operand.Imm)

    @staticmethod
    def opcode() -> int: return 0x1

@dataclasses.dataclass()
class MovReg(Instruction):
    reg_0: int
    reg_1: int
    
    @staticmethod
    def mnemonic() -> str: return 'movr'
    
    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg, Operand.Reg)
    
    @staticmethod
    def opcode() -> int: return 0x2

@dataclasses.dataclass()
class LoadReg(Instruction):
    reg_0: int
    reg_1: int
    
    @staticmethod
    def mnemonic() -> str: return 'ldr'
    
    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg, Operand.Reg)
    
    @staticmethod
    def opcode() -> int: return 0x3

@dataclasses.dataclass()
class StoreReg(Instruction):
    reg_0: int
    reg_1: int
    
    @staticmethod
    def mnemonic() -> str: return 'str'
    
    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg, Operand.Reg)
    
    @staticmethod
    def opcode() -> int: return 0x4

@dataclasses.dataclass()
class Add(Instruction):
    reg_0: int
    reg_1: int
    reg_2: int
    
    @staticmethod
    def mnemonic() -> str: return 'add'
    
    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg, Operand.Reg, Operand.Reg)
    
    @staticmethod
    def opcode() -> int: return 0x5

@dataclasses.dataclass()
class Mul(Instruction):
    reg_0: int
    reg_1: int
    reg_2: int
    
    @staticmethod
    def mnemonic() -> str: return 'mul'
    
    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg, Operand.Reg, Operand.Reg)
    
    @staticmethod
    def opcode() -> int: return 0x6

@dataclasses.dataclass()
class Not(Instruction):
    reg_0: int
    reg_1: int
    
    @staticmethod
    def mnemonic() -> str: return 'not'
    
    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg, Operand.Reg)
    
    @staticmethod
    def opcode() -> int: return 0x7

@dataclasses.dataclass()
class And(Instruction):
    reg_0: int
    reg_1: int
    reg_2: int
    
    @staticmethod
    def mnemonic() -> str: return 'and'
    
    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg, Operand.Reg, Operand.Reg)
    
    @staticmethod
    def opcode() -> int: return 0x8

@dataclasses.dataclass()
class Or(Instruction):
    reg_0: int
    reg_1: int
    reg_2: int
    
    @staticmethod
    def mnemonic() -> str: return 'or'
    
    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg, Operand.Reg, Operand.Reg)
    
    @staticmethod
    def opcode() -> int: return 0x9

@dataclasses.dataclass()
class Xor(Instruction):
    reg_0: int
    reg_1: int
    reg_2: int
    
    @staticmethod
    def mnemonic() -> str: return 'xor'
    
    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg, Operand.Reg, Operand.Reg)
    
    @staticmethod
    def opcode() -> int: return 0xa

@dataclasses.dataclass()
class ShiftL(Instruction):
    reg_0: int
    reg_1: int
    reg_2: int
    
    @staticmethod
    def mnemonic() -> str: return 'shl'
    
    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg, Operand.Reg, Operand.Reg)
    
    @staticmethod
    def opcode() -> int: return 0xb

@dataclasses.dataclass()
class ShiftR(Instruction):
    reg_0: int
    reg_1: int
    reg_2: int
    
    @staticmethod
    def mnemonic() -> str: return 'shr'
    
    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg, Operand.Reg, Operand.Reg)
    
    @staticmethod
    def opcode() -> int: return 0xc

@dataclasses.dataclass()
class Jump(Instruction):
    reg_0: int
    
    @staticmethod
    def mnemonic() -> str: return 'jmp'
    
    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg,)
    
    @staticmethod
    def opcode() -> int: return 0xd

@dataclasses.dataclass()
class JumpEq(Instruction):
    reg_0: int
    reg_1: int
    reg_2: int
    
    @staticmethod
    def mnemonic() -> str: return 'jeq'
    
    @staticmethod
    def operands() -> tuple[Operand, ...]: return (Operand.Reg, Operand.Reg, Operand.Reg)
    
    @staticmethod
    def opcode() -> int: return 0xe


MNEMONIC_TO_INSTR: dict[str, type[Instruction]]= {
    Halt.mnemonic()    : Halt,
    MovImm.mnemonic()  : MovImm,
    MovReg.mnemonic()  : MovReg,
    LoadReg.mnemonic() : LoadReg,
    StoreReg.mnemonic(): StoreReg,
    Add.mnemonic()     : Add,
    Mul.mnemonic()     : Mul,
    Not.mnemonic()     : Not,
    And.mnemonic()     : And,
    Or.mnemonic()      : Or,
    Xor.mnemonic()     : Xor,
    ShiftL.mnemonic()  : ShiftL,
    ShiftR.mnemonic()  : ShiftR,
    Jump.mnemonic()    : Jump,
    JumpEq.mnemonic()  : JumpEq,
}

REG_NUM_MAP: dict[str, int] = {
    'r0': 0x0,
    'r1': 0x1,
    'r2': 0x2,
    'r3': 0x3,
    'sp': 0x4,
    'fp': 0x5,
}

@dataclasses.dataclass
class ParseError:
    msg: str

@dataclasses.dataclass
class ParsedASM:
    data_labels: dict[str, int]
    data: list[int]

    instr_labels: dict[str, int]
    instrs: list[Instruction]

class ParserMode(enum.StrEnum):
    TEXT = 'text'
    DATA = 'data'

class Parser:
    WHITESPACE_PAT = re.compile(r'\s+')
    LINE_PAT = re.compile(r'.*?(\n|$)')
    NUMBER_PAT = re.compile(r'(0b[01]+)|(0x[0-9a-fA-F]+)|(0o[0-7]+)|(\d+)')

    def __init__(self, src: str):
        self.src = src
        self.idx = 0
        self.line = 0
        self.mode = ParserMode.TEXT

        self.curr_data_offset = 0
        self.data_labels: dict[str, int] = {}
        self.data: list[int] = []

        self.curr_instr_offset = 0
        self.instr_labels: dict[str, int] = {}
        self.instrs: list[Instruction] = []

    def parse(self) -> ParsedASM | ParseError:
        while self.idx < len(self.src):
            if self.expect(r'.data') is not None:
                self.mode = ParserMode.DATA
                continue

            if self.expect(r'.text') is not None:
                self.mode = ParserMode.TEXT
                continue

            if (_ := self.expect(r'#.*?(\n|$)')) is not None:
                continue

            if self.mode == ParserMode.DATA:
                if (err := self.parse_dataline()) is not None:
                    return err
                continue

            if self.mode == ParserMode.TEXT:
                if (err := self.parse_textline()) is not None:
                    return err
                continue

        return ParsedASM(self.data_labels, self.data, self.instr_labels, self.instrs)



    def parse_dataline(self) -> None | ParseError:
        label = self.parse_label()
        if isinstance(label, ParseError):
            return label

        data = self.parse_data()
        if isinstance(data, ParseError):
            return data

        self.data_labels[label] = self.curr_data_offset
        self.curr_data_offset += len(data)
        self.data += data


    def parse_data(self) -> list[int] | ParseError:
        if self.expect(r'\[') is None:
            return ParseError(f"Expected '[' on line {self.line + 1}.")

        data = []
        while True:
            if (n := self.expect(Parser.NUMBER_PAT)) is None:
                return ParseError(f"Expected a number on line {self.line + 1}.")

            try:
                n = int(n, base=0)
            except Exception:
                return ParseError(f"Bad number '{n}' on line {self.line + 1}.")

            data.append(n)

            if self.expect(r',?\s*\]') is not None:
                break


            if self.expect(r',') is None:
                return ParseError(f"Expected ',' on line {self.line + 1}.")

        return data
        


    def parse_textline(self) -> None | ParseError:
        if self.check(r'label'):
            label = self.parse_label()
            if isinstance(label, ParseError):
                return label

            self.instr_labels[label] = self.curr_instr_offset
            return

        instr = self.parse_instr();
        if isinstance(instr, ParseError):
            return instr

        operands = self.parse_operands(instr);
        if isinstance(operands, ParseError):
            return operands

        self.instrs.append(instr(*operands))
        self.curr_instr_offset += len(instr.operands()) + 1


    def parse_instr(self) -> type[Instruction] | ParseError:
        mnemonic = self.expect(r'\w+')
        if mnemonic is None:
            return ParseError(f"Expected an instruction mnemonic on line {self.line + 1}.")

        if (instr := MNEMONIC_TO_INSTR.get(mnemonic)) is None:
            return ParseError(f"Bad instruction mnemonic on line {self.line + 1}.")

        return instr

    def parse_operands(self, instr: type[Instruction]) -> list[Operand] | ParseError:
        operands = []
        for idx, exp_operand in enumerate(instr.operands()):
            if exp_operand == Operand.Reg:
                if (reg := self.expect(r'(R[0-3])|(SP)|(FP)')) is None:
                    return ParseError(f"Expected a register for operand {idx + 1} of '{instr.mnemonic()}' on line {self.line + 1}.")

                operands.append(REG_NUM_MAP[reg.lower()])

            if exp_operand == Operand.Imm:
                if (imm := self.expect(Parser.NUMBER_PAT)) is not None:
                    operands.append(int(imm, base=0))
                elif (label := self.expect(r'@\w+')) is not None:
                    operands.append(label[1:])
                else:
                    return ParseError(f"Expected an immediate or label for operand {idx + 1} of '{instr.mnemonic()}' on line {self.line}.")

                    
            if idx < len(instr.operands()) - 1 and self.expect(r',') is None:
                return ParseError(f"Expected ',' on line {self.line + 1}.")

        return operands
        


    def parse_label(self) -> str | ParseError:
        if self.expect(r'label') is None:
            return ParseError(f"Expected 'label' instead on line {self.line + 1}.")

        if (name := self.expect(r'\w+:')) is None:
            return ParseError(f"Expected a label name on line {self.line + 1}.")

        return name[:-1]

    def expect(self, pat: re.Pattern | str) -> str | None:
        if (m := re.match(pat, self.src[self.idx:])) is not None:
            self.line += m[0].count('\n')
            self.idx += m.end(0)
            self.skip_whitespace()
            return m[0]

        return None

    def check(self, pat: re.Pattern | str) -> bool:
        return re.match(pat, self.src[self.idx:]) is not None

    def skip_whitespace(self):
        if (m := re.match(Parser.WHITESPACE_PAT, self.src[self.idx:])) is not None:
            self.line += m[0].count('\n')
            self.idx += m.end(0)

def parse_file(filename: str) -> ParsedASM:
    with open(filename, 'r') as f:
        return Parser(f.read()).parse()

def generate_bytecode(parsed_asm: ParsedASM) -> list[int] | ParseError:
    instrs_len = sum(len(instr) for instr in parsed_asm.instrs)
    bytecode: list[int] = []
    for instr in parsed_asm.instrs:
        bytecode.append(instr.opcode())
        match instr:
            case Halt(reg_0): bytecode += [reg_0]
            case MovImm(reg_0, str(imm)):
                if imm in parsed_asm.data_labels:
                    bytecode += [reg_0, parsed_asm.data_labels[imm] + instrs_len]

                elif imm in parsed_asm.instr_labels:
                    bytecode += [reg_0, parsed_asm.instr_labels[imm]]
                else:
                    return ParseError(f"Label '{imm}' does not exist.")
            case MovImm(reg_0, int(imm)): bytecode += [reg_0, imm]

            case MovReg(reg_0, reg_1):   bytecode += [reg_0, reg_1]
            case LoadReg(reg_0, reg_1):  bytecode += [reg_0, reg_1]
            case StoreReg(reg_0, reg_1): bytecode += [reg_0, reg_1]

            case Add(reg_0, reg_1, reg2): bytecode += [reg_0, reg_1, reg2]
            case Mul(reg_0, reg_1, reg2): bytecode += [reg_0, reg_1, reg2]
            case Not(reg_0, reg_1):       bytecode += [reg_0, reg_1]
            case And(reg_0, reg_1, reg2): bytecode += [reg_0, reg_1, reg2]
            case Or(reg_0, reg_1, reg2):  bytecode += [reg_0, reg_1, reg2]
            case Xor(reg_0, reg_1, reg2): bytecode += [reg_0, reg_1, reg2]

            case ShiftL(reg_0, reg_1, reg2): bytecode += [reg_0, reg_1, reg2]
            case ShiftR(reg_0, reg_1, reg2): bytecode += [reg_0, reg_1, reg2]

            case Jump(reg_0): bytecode += [reg_0]
            case JumpEq(reg_0, reg_1, reg_2): bytecode += [reg_0, reg_1, reg_2]

    bytecode += parsed_asm.data
    return bytecode

def reformat_bytecode(bytecode: list[int]) -> str:
    # They're saying this is the worst line of code ever written
    # Asked to leave the Python community
    return f'List<{','.join(int_to_list_format(byte) for byte in bytecode)}>'

def int_to_list_format(n) -> str:
    return f'List<{','.join({'0': 'BitZ', '1': 'BitO'}[bit] for bit in f'{n:b}'[::-1])}>'

if __name__ == '__main__':
    import argparse
    ascii_art = (
r"""
   |\---/|
   | ,_, |
    \_`_/-..----.
 ___/ `   ' ,""+ \  sk
(__...'   __\    |`.___.';
  (_,...'(_,.`__)/'.....+
"""
)
    parser = argparse.ArgumentParser(
        prog="Assembler",
        description="Assembler for Grace's Ad-hoc Assembly\n"+ascii_art,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('filename', help="Path to assembly file")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-i', '--intcode',  action='store_true',  dest='outints')
    group.add_argument('-t', '--typecode', action='store_false', dest='outints')
    group.set_defaults(outbytes=False)
    args = parser.parse_args()

    asm = parse_file(args.filename)
    if isinstance(asm, ParseError):
        print(asm)
        exit()
    intcode = generate_bytecode(asm)
    if isinstance(intcode, ParseError):
        print(intcode)
        exit()

    if args.outints:
        with open(f'{args.filename.split('.')[0]}.ic', 'w') as f:
            f.write(';'.join(str(n) for n in intcode))
        pass
    else:
        reformatted = reformat_bytecode(intcode)
        with open(f'{args.filename.split('.')[0]}.tc', 'w') as f:
            f.write(f'using ProgramCounter = List<BitZ>;\n')
            f.write(f'using Registers = List<{','.join('List<BitZ>' for _ in range(4))}, {','.join(int_to_list_format(len(intcode)+12) for _ in range(2))}>;\n')
            f.write(f'using InitialMemory = {reformatted};')
