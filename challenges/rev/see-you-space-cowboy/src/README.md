# For Future Reference on How to Rebuild This Challenge
1. Run `./assembler.py coloring.baasm`
2. Copy and Paste `coloring.tc` to `space_cowboy.cpp`
3. Reobfuscate `space_cowboy.cpp`
  - `ProgramCounter` to `Yunyu`
  - `Registers` to `Xuangue`
  - `InitialMemory` to `Zosma`
  - `List` to `Achernar`
  - `BitZ` to `Acamar`
  - `BitO` to `Absolutno`

## Creating Another Program
1. Write your program in `Grace's Ad-hoc Assembly`
  - Look at `coloring.baasm` for an example of Grace's Ad-hoc Assembly.
2. Run `./assembler.py [your file].baasm` to create a `[your file].tc`
  - Run `./assembler.py --intcode [your file].baasm` to create a `[your file].ic`
  - You can run `./vm.py [your file].ic` to run your program

## Other Stuff
- `generate_xored_flag.py` is used to create a flag for the challenge
- The current challenge uses a 4x4 Sudoku puzzle:
```
  - + - + - + -          - + - + - + -  
|   | 3 |   |   |      | 4 | 3 | 2 | 1 |
+ - + - + - + - +      + - + - + - + - +
| 1 |   |   |   |      | 1 | 2 | 3 | 4 |
+ - + - + - + - +  ->  + - + - + - + - +
|   |   | 4 |   |      | 3 | 1 | 4 | 2 |
+ - + - + - + - +      + - + - + - + - +
| 2 |   |   |   |      | 2 | 4 | 1 | 3 |
  - + - + - + -          - + - + - + -  
```
