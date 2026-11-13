# See You Space Cowboy

**Category**: Rev  
**Difficulty**: Insane  
**Author**: Grace

## Description

Some kid named Edward keeps making insane programs to try and defend against ICARUS. They're
actually pretty effective, but the problem is that only Edward can understand what his programs are
doing!!! I managed to find one of the easier-looking ones, but it's still pretty mystical. If we can
understand what they do, maybe we could learn how to defend ourselves more effectively.

Try and find out what the program does. **I should tell you to be cautious when running the program.
I tried running it and it can eat up your RAM pretty quick if you're not careful.**

## Files Provided

- `space_cowboy.cpp`
- `Makefile`

## Tools Used

- python

## Flag

`flag{c++_is_an_interpreted_langauge}`

## Solution

**NOTE**: This challenge is super very inspired by Perfect Blue's writeup of PlaidCTF's "[That's a
Lot of Fish](https://blog.perfect.blue/Lot-of-Fish-PlaidCTF-2020)" from 2020. It's basically the
same challenge but in C++ and a different program.

### Reversing `space_cowboy.cpp`
We are given `space_cowboy.cpp` which is a massive C++ file:
```cpp
#include <iostream>
#include <cxxabi.h>
#include <cstdint>
struct Absolutno {};
struct Acamar {};
template<typename... Xs> struct Achernar {};
using Alasia = Achernar<Acamar>;
using Holoea = Achernar<Absolutno>;
using BarnardsStar = Achernar<Acamar, Absolutno>;
using Guahayona = Achernar<Absolutno, Absolutno>;
using ButterflyStar = Achernar<Acamar, Acamar, Absolutno>;
using Caph = Achernar<Absolutno, Acamar, Absolutno>;
using Kronos = Achernar<Acamar, Absolutno, Absolutno>;
using Cexing = Achernar<Absolutno, Absolutno, Absolutno>;
using LaSuperba = Achernar<Acamar, Acamar, Acamar, Absolutno>;
using Gouguo = Achernar<Absolutno, Acamar, Acamar, Absolutno>;
using Cocibolca = Achernar<Acamar, Absolutno, Acamar, Absolutno>;
using Copernicus = Achernar<Absolutno, Absolutno, Acamar, Absolutno>;
using Lerna = Achernar<Acamar, Acamar, Absolutno, Absolutno>;
using DustBall = Achernar<Absolutno, Acamar, Absolutno, Absolutno>;
using Diya = Achernar<Acamar, Absolutno, Absolutno, Absolutno>;
using Lich = Achernar<Absolutno, Absolutno, Absolutno, Absolutno>;
template<typename L> struct Electra {};
template<typename... Bits> struct Electra<Achernar<Absolutno, Bits...>> { static constexpr std::uint64_t res = (Electra<Achernar<Bits...>>::res << 1) | 1; };
template<typename... Bits> struct Electra<Achernar<Acamar, Bits...>> { static constexpr std::uint64_t res = (Electra<Achernar<Bits...>>::res << 1) | 0; };
template<> struct Electra<Alasia> { static constexpr std::uint64_t res = 0; };
template<> struct Electra<Holoea> { static constexpr std::uint64_t res = 1; };
template<typename Merak, typename Minchir, typename Petra> struct LionRock {};
template<typename Minchir, typename Petra> struct LionRock<Acamar, Minchir, Petra> { using res = Petra; };
template<typename Minchir, typename Petra> struct LionRock<Absolutno, Minchir, Petra> { using res = Minchir; };
template<typename Peacock, typename Polaris> struct Vega {};
template<typename... Scheat, typename... Shangcheng> struct Vega<Achernar<Scheat...>, Achernar<Shangcheng...>> { using res = Achernar<Scheat..., Shangcheng...>; };
template<typename Kuda> struct Heze {};
template<typename Fomalhaut, typename... Intercrus> struct Heze<Achernar<Fomalhaut, Intercrus...>> { using res = Fomalhaut; };
template<typename Markab> struct Maia {};
template<typename Ligong, typename... Merga> struct Maia<Achernar<Ligong, Merga...>> { using res = typename Maia<Achernar<Merga...>>::res; };
template<typename Zaurak> struct Maia<Achernar<Zaurak>> { using res = Zaurak; };
template<typename Weixiu> struct Irena {};
...
```

This was all in one line, but I broke it up so it's a little more readable. It's a lot of templating
stuff. If we scroll down more, we can see the main function:
```cpp
int main() {
    Rukbat<Pili<Yunyu, Xuangue, typename Vega<Zosma, typename Vega<Input, Algol>::res>::res>>::res::output();
}
```

It seems like it's creating one of the structs from above and doing some templating shenanigans.

We are also given a `Makefile`:
```Makefile
space_cowboy: space_cowboy.cpp
	g++ space_cowboy.cpp -ftemplate-depth=9999999 -o space_cowboy
```

So the program is doing a lot of nested templating. The next step is to figure out what the
templating stuff is doing. If we look at lines 4-22 we see:
```cpp
struct Absolutno {};
struct Acamar {};
template<typename... Xs> struct Achernar {};
using Alasia        = Achernar<Acamar>;
using Holoea        = Achernar<Absolutno>;
using BarnardsStar  = Achernar<Acamar,    Absolutno>;
using Guahayona     = Achernar<Absolutno, Absolutno>;
using ButterflyStar = Achernar<Acamar,    Acamar,    Absolutno>;
using Caph          = Achernar<Absolutno, Acamar,    Absolutno>;
using Kronos        = Achernar<Acamar,    Absolutno, Absolutno>;
using Cexing        = Achernar<Absolutno, Absolutno, Absolutno>;
using LaSuperba     = Achernar<Acamar,    Acamar,    Acamar,    Absolutno>;
using Gouguo        = Achernar<Absolutno, Acamar,    Acamar,    Absolutno>;
using Cocibolca     = Achernar<Acamar,    Absolutno, Acamar,    Absolutno>;
using Copernicus    = Achernar<Absolutno, Absolutno, Acamar,    Absolutno>;
using Lerna         = Achernar<Acamar,    Acamar,    Absolutno, Absolutno>;
using DustBall      = Achernar<Absolutno, Acamar,    Absolutno, Absolutno>;
using Diya          = Achernar<Acamar,    Absolutno, Absolutno, Absolutno>;
using Lich          = Achernar<Absolutno, Absolutno, Absolutno, Absolutno>;
```

If you're a nerd, this should look pretty familiar. It's counting from 0 to 15 in binary, with
`Acamar` representing 0 and `Absolutno` representing 1. `Achernar` seems to be some kind of
container for these types, probably a list. So let's rename some stuff:
```cpp
struct BitO {};
struct BitZ {};
template<typename... Xs> struct List {};
using Bin0 = List<BitZ>;
using Bin1 = List<BitO>;
using Bin2 = List<BitZ, BitO>;
using Bin3 = List<BitO, BitO>;
using Bin4 = List<BitZ, BitZ, BitO>;
using Bin5 = List<BitO, BitZ, BitO>;
using Bin6 = List<BitZ, BitO, BitO>;
using Bin7 = List<BitO, BitO, BitO>;
using Bin8 = List<BitZ, BitZ, BitZ, BitO>;
using Bin9 = List<BitO, BitZ, BitZ, BitO>;
using BinA = List<BitZ, BitO, BitZ, BitO>;
using BinB = List<BitO, BitO, BitZ, BitO>;
using BinC = List<BitZ, BitZ, BitO, BitO>;
using BinD = List<BitO, BitZ, BitO, BitO>;
using BinE = List<BitZ, BitO, BitO, BitO>;
using BinF = List<BitO, BitO, BitO, BitO>;
```

So it's representing numbers at the type-level. We can keep going and reversing what each
template/struct does. There's a lot so i'll just do another one.

```cpp
template<typename BitA, typename BitB, typename BitC> struct Mazaalai {};
template<> struct Mazaalai<BitZ, BitZ, BitZ> { using res = BitZ; using cout = BitZ; };
template<> struct Mazaalai<BitZ, BitZ, BitO> { using res = BitO; using cout = BitZ; };
template<> struct Mazaalai<BitZ, BitO, BitZ> { using res = BitO; using cout = BitZ; };
template<> struct Mazaalai<BitZ, BitO, BitO> { using res = BitZ; using cout = BitO; };
template<> struct Mazaalai<BitO, BitZ, BitZ> { using res = BitO; using cout = BitZ; };
template<> struct Mazaalai<BitO, BitZ, BitO> { using res = BitZ; using cout = BitO; };
template<> struct Mazaalai<BitO, BitO, BitZ> { using res = BitZ; using cout = BitO; };
template<> struct Mazaalai<BitO, BitO, BitO> { using res = BitO; using cout = BitO; };

template<typename Koeia, typename Komondor, typename Kornephoros>
struct Libertas {
private:
    using op = Mazaalai<typename Head<Koeia>::res, typename Head<Komondor>::res, Kornephoros>;
public:
    using res = typename Concat<
        List<typename op::res>,
        typename Libertas<
            typename Tail<Koeia>::res,
            typename Tail<Komondor>::res,
            typename op::cout
        >::res
    >::res;
};

...

template<> struct Libertas<List<>, List<>, BitZ> {
    using res = List<>;
};
```

This is a lot, so let's focus on `Mazaalai`
```cpp
template<typename BitA, typename BitB, typename BitC> struct Mazaalai {};
template<> struct Mazaalai<BitZ, BitZ, BitZ> { using res = BitZ; using cout = BitZ; };
template<> struct Mazaalai<BitZ, BitZ, BitO> { using res = BitO; using cout = BitZ; };
template<> struct Mazaalai<BitZ, BitO, BitZ> { using res = BitO; using cout = BitZ; };
template<> struct Mazaalai<BitZ, BitO, BitO> { using res = BitZ; using cout = BitO; };
template<> struct Mazaalai<BitO, BitZ, BitZ> { using res = BitO; using cout = BitZ; };
template<> struct Mazaalai<BitO, BitZ, BitO> { using res = BitZ; using cout = BitO; };
template<> struct Mazaalai<BitO, BitO, BitZ> { using res = BitZ; using cout = BitO; };
template<> struct Mazaalai<BitO, BitO, BitO> { using res = BitO; using cout = BitO; };
```

If you've taken CSCE 21104, this should also look pretty familiar; it's a full adder! So let's
rename it to `AddOp`:

```cpp
template<typename BitA, typename BitB, typename BitC> struct AddOp {};
template<> struct AddOp<BitZ, BitZ, BitZ> { using res = BitZ; using cout = BitZ; };
template<> struct AddOp<BitZ, BitZ, BitO> { using res = BitO; using cout = BitZ; };
template<> struct AddOp<BitZ, BitO, BitZ> { using res = BitO; using cout = BitZ; };
template<> struct AddOp<BitZ, BitO, BitO> { using res = BitZ; using cout = BitO; };
template<> struct AddOp<BitO, BitZ, BitZ> { using res = BitO; using cout = BitZ; };
template<> struct AddOp<BitO, BitZ, BitO> { using res = BitZ; using cout = BitO; };
template<> struct AddOp<BitO, BitO, BitZ> { using res = BitZ; using cout = BitO; };
template<> struct AddOp<BitO, BitO, BitO> { using res = BitO; using cout = BitO; };
template<typename Koeia, typename Komondor, typename Kornephoros>

template<typename Koeia, typename Komondor, typename Kornephoros>
struct Libertas {
private:
    using op = AddOp<typename Head<Koeia>::res, typename Head<Komondor>::res, Kornephoros>;
public:
    using res = typename Concat<
        List<typename op::res>,
        typename Libertas<
            typename Tail<Koeia>::res,
            typename Tail<Komondor>::res,
            typename op::cout
        >::res
    >::res;
};
...
```
So, `Libertas` seems to be using `AddOp` a lot. If we look at the first `Libertas` struct:
- It's concatenating the result of the `AddOp`, `op::res`, and the result of the recursive "call"
to `Libertas` again.
- We see that the last type in the recursive call is `op::cout`, so the `Kornephoros` must
represent the previous call's `op::cout`.
- It calls
[`Head`](https://hackage-content.haskell.org/package/base-4.22.0.0/docs/Prelude.html#v:head) and
[`Tail`](https://hackage-content.haskell.org/package/base-4.22.0.0/docs/Prelude.html#v:tail) on
`Koeia` and `Komondor`, so `Koeia` and `Komondor` are probably supposed to be a list of bits.

With these observations, we can guess that `Libertas` is a ripple carry adder and we can rename
things appropriately:
```cpp
template<typename BinA, typename BinB, typename CarryBit>
struct AddC {
private:
    using op = AddOp<typename Head<BinA>::res, typename Head<BinB>::res, CarryBit>;
public:
    using res = typename Concat<
        List<typename op::res>,
        typename AddC<
            typename Tail<BinA>::res,
            typename Tail<BinB>::res,
            typename op::cout
        >::res
    >::res;
};
```

Check the `space_cowboy-annotated.cpp` to find the version with all the structs named appropriately.
You'll find that it is a virtual machine that's running a program. There is also an `Input`
typealias where we can put in an input for the program before it runs. Now our goal is to understand
what that program is doing.

### Reversing the Program in `space_cowboy.cpp`
The program is contained in the memory of the virtual machine. Since we understand how the virtual
machine works, we can just map the contents in memory to readable "assembly" instructions that the
virtual machine uses. Check `coloring.baasm` for the disassembly.

One thing to note is that the instructions and data are all in the same memory "pool," so if we
naively try to just map the stuff in memory, we will get a lot of junk and invalid instructions. But
if you analyze the disassembly, you'll notice that the program will halt at a certain point, so we
can guess that the stuff after that is just data. There's also instructions in the program that
accesses that part of the program and treats it as data, so that's another clue.

I'm too lazy to comb through the program and explain each bit, so i'll just explain the high level
of it:
- The program goes through a list of numbers, `E`,  by two which is used to index another list, `N`.
- For each of the two numbers indexed from `N`, they are compared and check to see if they're the
same.
  - If they are the same, the program halts and prints out "Bad Colors!".
  - If they are not the same, the program continues.
- This is a graph coloring problem!
- Since our input is appended to the end of `N`, we can assume that we have to fill out the "colors"
  of the rest of the nodes. By analyzing the program, there it checks only a total of 16 different
  nodes. The first four are already filled in so we only need to input 12 more nodes.
- After the progam verifies the colorings are correct, it concatenates the nodes into a 32-bit
  number and runs a linear congruential generator (LCG) 255 times using that 32-bit number as the
  seed.
- It then uses the result from the LCG to XOR some stuff in memory and prints that out.

So basically, we just need to solve the graph coloring problem and run the program.
If you lay out the graph, you'll see that it's actually a 4x4 sudoku problem which we can easily
solve:
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

If we try to input that into `space_cowboy.cpp` and compile it, it will take an insane amount of
memory and take forever to compile it. So it is better to rewrite the virtual machine in a saner way
and run the program.

`vm.py` is the virtual machine rewritten in Python, and `coloring-solved.ic` is the program with
solved inputs in `space_cowboy.cpp` converted to a format `vm.py` can understand.

So, if we run `./vm.py coloring-solved.ic` we get the output `flag{c++_is_an_interpreted_langauge}`.

Hurray.

## Solve Script

Run `./vm.py coloring-solved.ic`

We assume that `coloring-solved.ic` is created by the participant based reverse engineering the
problem.

## Technique/Tags

`c++`; `templates`; `reverse-engineering`; `functional-programming`

## Setup / Deployment Notes

N/A

## Known Issues / Notes

Be careful if you try to compile `space_cowboy.cpp` ! It'll take up all of your memory if you add in
the correct inputs.
