
ChallengeSolution-XenoInstructions_3.md  
-------------

## ChallengeName  
XenoInstructions #3  

**Category:**    Rev (Reverse Engineering)  
**Difficulty:**  insane  
**Author:**      "Mort (StevieoXOR)"  

### ChallengeDescription_Themed_ViewableByParticipant  
Our crew has reconstructed a program that resembles Assembly, but coded in a Functional Paradigm that defines and runs anonymous functions. However, the reconstructed code is still missing an Interpreter and microcode compiler. Can you figure out how to run the program? You should round the program's final output value (do not include any intermediary computations) to the nearest 100 (either with comma or without are both okay), and then wrap that rounded value in the text "flag{" and "}". If the final output value is a Complex Number (i.e., has both Real AND Imaginary parts), then you should round each component to the nearest 100 (fancy vector magnitude math is NOT needed), such as "flag{-19,200}", "flag{19200}", "flag{-19,200i}", "flag{19200i}", "flag{100+19,200i}", "flag{100+19200i}", "flag{-100-19200i}".  

### FilesProvidedToParticipant  
* dist/XI3-barely__function-al.__program.asm  

### Flags that participant can submit  
* flag{4575.852}  
* flag{4575}  
* flag{4576}  
* flag{4500}  
* flag{4600}  
* flag{4575.852+0i}  
* flag{4575+0i}  
* flag{4576+0i}  
* flag{4500+0i}  
* flag{4600+0i}  
* flag{4,575.852}  
* flag{4,575}  
* flag{4,576}  
* flag{4,500}  
* flag{4,600}  
* flag{4,575.852+0i}  
* flag{4,575+0i}  
* flag{4,576+0i}  
* flag{4,500+0i}  
* flag{4,600+0i}  





# Solution  


## TL;DR  

* The flag is the result of calling all the instructions listed in the program (making sure to call them in the correct order and interpret the parameters' positions correctly), and then wrapping that value in `flag{` and `}`.  
  * Just like in XenoInstructions #2, ALL the instructions will need to be executed. Additionally, participant must run the same instructions in the order: `0 2 4 6 8 ... 9 7 5 3 1` rather than order `0 1 2 3 4 5 ...`.  
  * These instructions still execute sequentially, from left to right. However, the parsing of each substituted value during each instruction is where this challenge differs from the previous challenges.









## FullSolution Explanation

0-ary/nullary, unary, binary, ternary, unary, unary, binary, quaternary, binary, null
* Each of these corresponds to the **quantity** of arguments expected to be provided as input.

# Explanation of the set of functions
```
.fun:
a,b,c,d -> a*b/c-d
// ^^^ Has a,b,c,d:	4 unique inputs -> is a quaternary function

a,x,z -> z+a+x*log(x)
// ^^^ Has z,a,x:	3 unique inputs -> is a ternary function
// ^^^ The ordering of the inputs is z,a,x, rather than a,x,z, makes a difference. Inputs are still interpreted as most-recently-computed-function's result, but those results' ordering is determined alphabetically rather than by left-to-right.
// ^^^ log(x) is assumed to be "log Base10 (of x)", not "log BaseE" nor "log Base2".

d,f -> sqrt(d+d*f)
// ^^^ Has d,f:		2 unique inputs -> is a binary function

e -> e+e+e
// ^^^ Has e:		1 unique input -> is a unary function

ABSENCE -> STARTNUM
// ^^^ Has nothing:	0 unique inputs -> is a nullary function
```

Notice how there are not *multiple* functions that happen to take the same # of arguments.  
* I.e., the following doesn't appear in the program at the same time:  
  * e -> e+e+e	// Unary  
  * a -> a+a+a	// [WARNING] AMBIGUOUS: UNARY FUNCTION ALREADY DEFINED  

Each function outputs a SINGLE value, not two or three or four values.  
* So, how does the code executor know how to deal with any function other than a unary function?  
* I decided to make it where `Null Un Bin Tern Un` searches in the following order:  
  * Un looks at Null  
  * Bin looks at Un, and then Null  
  * Tern looks at Bin, and then Un, and then Null  
  * The very last (i.e., rightmost) Un will look at its previous instruction for obtaining an input value, which happens to be Tern.  
  * The very last instruction is Null, which does NOT take any inputs. Therefore, the last instruction does NOT depend on any of the program's previous instructions.  



The square brackets [...] serve as a "goto"/"dereference" operator.  

Each block of text that (begins with a ".", followed by a word that contains no space-like characters) is a "section" of code/text that can be navigated to (by wrapping that label in square brackets).  

The ".comment" section indicates to be aware of OrderOfOperations. There are two typical OOO conventions:  
* left-to-right  
* PEMDAS (Parentheses, Exponents, Multiplication&Division_Equally, Addition&Subtraction_Equally)  

I "invented" another OOO, where parsing happens by collapsing the leftmost term, then the rightmost term, then the leftmost term, then the rightmost term, then repeat. I call this "Collapse".  
* E.g., `1+2+3+4+5` gets parsed as `(1+2)+3+4+5` -> `(1+2)+3+(4+5)` -> `((1+2)+3)+(4+5)` -> (next step can't be (3)+(4+5) because you'd have to enter inside a group of already-established parentheses, which can't happen since that group of values inside the parentheses was *already resolved* to a single number) -> `(((1+2)+3)+(4+5))`  
* Side-note:  
  * How would this work in real-life?  
  * Probably a weird implementation of a stack where the parser knows exactly how long each line of code is, and then indexes into each symbol according to the start and end of each line, like Python's 0, -1, 1, -2, 2, -3, ....  

You might need to try each OOO definition, if the flag you get after computing ends up being wrong.  
* This challenge uses "Collapse" first (never LTR), and when "Collapse" can't reasonably apply (e.g., function calls), then PEMDAS (specifically the Parentheses part) takes over.  





## Step-by-step analysis of solving the program  

1) Null  
* `=STARTNUM`  

2) Null Un  
* `=[STARTNUM]->[e+e+e]`  

3) Null Un Bin  
* `=[STARTNUM]->[e+e+e]->[sqrt(d+d*f)]`  

...  



# Program's Instructions:  
==  
Null Un Bin Tern Un Un Bin Quatern Bin Null  

==  
0 1 2 3 1  1 2 4 2 0  

== (after identifying the functions that correspond to the digits above)  

Naively:  
(STARTNUM)->(e+e+e)->(sqrt(d+d*f))->(z+a+x^x)->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a*b/c-d)->(sqrt(d+d*f))->(STARTNUM)  

Reordered according to CollapseLeftmost, ThenCollapseRightmost, ThenRepeatThePreviousTwoSteps:  

==  
0 1 2 3 1  1 2 4 2 0  
=>  
==  
A B C D E  F G H I J  
0 1 2 3 1  1 2 4 2 0  
=>  
A J  B I  C H  D G  E F  
=>  
0 0  1 2  2 4  3 2  1 1  

Okay, so we now have the correct order of instructions (i.e., the correct order of function calls).  

==  
42->42->(e+e+e)->(sqrt(d+d*f))->(sqrt(d+d*f))->(a*b/c-d)  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  

Okay, so now we've substituted each instruction with the actual function that the instruction represented.  

Just like with the previous two challenges in this series, the most recently computed function's output gets assigned to be the leftmost variable in the function whose output we're trying to compute right now.  
* However, this can only happen *after* we've applied the CollapseLeftmost,CollapseRightmost,RepeatPreviousTwoSteps parser to the program's list of instructions.  

==  
42->42->(42+42+42)->(sqrt(d+d*f))->(sqrt(d+d*f))->(a*b/c-d)  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  


==  
42->42->(3*42)->(sqrt(d+d*f))->(sqrt(d+d*f))->(a*b/c-d)  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  


==  
42->42->126->(sqrt(d+d*f))->(sqrt(d+d*f))->(a*b/c-d)  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  


==  
42->42->126->(sqrt(126+126*42))->(sqrt(d+d*f))->(a*b/c-d)  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  

Now, even though this next result won't look different, the *way* it gets computed will be different.  
* This different evaluation *also* happened with the previous step of e+e+e, but addition is commutative, and addition was the only operation used in that instruction, so I ignored mentioning the computational ordering during that step.  


==  
42->42->126->(sqrt(252*42))->(sqrt(d+d*f))->(a*b/c-d)  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  

I collapsed 126+126*..., rather than collapsing ...+126*42.  
Sqrt() cannot be collapsed until the end of the instruction.  


==  
42->42->126->(sqrt(10,584))->(sqrt(d+d*f))->(a*b/c-d)  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  


==  
42->42->126->102.879->(sqrt(d+d*f))->(a*b/c-d)  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  


For the next instruction (and all other instructions), substitute parameters by most-recent instructions, nothing fancy...  
The "collapse the sides" part comes *after* the parameterValue substitutions have been performed.  


==  
42->42->126->102.879->(sqrt(102.879 + 102.879 * 126))->(a*b/c-d)  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  


==  
42->42->126->102.879->(sqrt(205.758 * 126))->(a*b/c-d)  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  

Now multiply the right side (126) by the left side (205.758) (not multiplying the left side by the right side since we just did that with 102+102) (again, you can't tell the difference in this instruction's result, since multiplication is commutative).  

==  
42->42->126->102.879->(sqrt(25,925.508))->(a*b/c-d)  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  

==  
42->42->126->102.879->161.014->(a*b/c-d)  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  












==  
42->42->126->102.879->161.014->(161.014 * 102.879 / 126 - 42)  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  


What sequence of steps are we going to perform to complete this instruction?  
#1) 161.014 * 102.879 (CollapseLeft)  
#2) 126 - 42 (notice how this was NOT flipped to become 42 - 126) (CollapseRight)  
#3) (161.014 * 102.879) / (126 - 42) (CollapseLeft, which appears equivalent to CollapseRight in this case)  



==  
42->42->126->102.879->161.014->(16,564.959 / 84)  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  


==  
42->42->126->102.879->161.014-> 197.202  
->(z+a+x*log(x))->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  




Now we need to know whether to honor an alphabetic ordering (a,x,z) or whether to keep doing LeftToRightSubstitution (z,a,x). Both techniques will still use the three most-recently-computed function results, but the order of those three results may differ. Up until now, the two techniques have had equivalent outcomes.  
We can assume that our microprocessor is powerful enough to automatically sort parameter names by ASCII values. `a` will be the most recently computed value, and then `x`, and then `z`.

When sorting alphabetically (which we have decided to use!):  
* `a` becomes 197.202  
* `x` becomes 161.014  
* `z` becomes 102.879  

When sorting by order of each parameter's occurrence in function's implementation:  
* `z` becomes 197.202  
* `a` becomes 161.014  
* `x` becomes 102.879  

==  
42->42->126->102.879->161.014 -> 197.202  
->(102.879 + 197.202 + 161.014 * log(161.014))  
->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  


Now that the values have been substituted, we need to apply the CollapseLeft, CollapseRight, Repeat technique.  
Order of collapses:  
#1) 102.879 + 197.202  
#2) 161.014 * log(161.014) (log(...) is a unary operation, not binary, so it is not treated, standalone, as a CollapseLeft nor CollapseRight)  
#3) (102.879 + 197.202) + (161.014 * log(161.014))  



==  
42->42->126->102.879->161.014 -> 197.202  
->(300.081 + 161.014 * log(161.014))  
->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  


==  
42->42->126->102.879->161.014 -> 197.202  
->(300.081 + 355.336)  
->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  


==  
42->42->126->102.879->161.014 -> 197.202  
->655.417  
->(sqrt(d+d*f))->(e+e+e)->(e+e+e)  


==  
42->42->126->102.879->161.014 -> 197.202  
->655.417  
->(sqrt(655.417 + 655.417 * 197.202))->(e+e+e)->(e+e+e)  


==  
42->42->126->102.879->161.014 -> 197.202  
->655.417  
->(sqrt(1,310.834 * 197.202))->(e+e+e)->(e+e+e)  


==  
42->42->126->102.879->161.014 -> 197.202  
->655.417  
->(sqrt(258,499.064))->(e+e+e)->(e+e+e)  


==  
42->42->126->102.879->161.014 -> 197.202  
->655.417  
->508.428->(e+e+e)->(e+e+e)  


==  
42->42->126->102.879->161.014 -> 197.202  
->655.417 -> 508.428
->(e+e+e)->(e+e+e)  


==  
42->42->126->102.879->161.014 -> 197.202  
->655.417 -> 508.428
->(3 * 508.428)->(e+e+e)  


==  
42->42->126->102.879->161.014 -> 197.202  
->655.417 -> 508.428
->1,525.284
->(e+e+e)  


==  
42->42->126->102.879->161.014 -> 197.202  
->655.417 -> 508.428
->1,525.284
->(3 * 1,525.284)  


==  
42->42->126->102.879->161.014 -> 197.202  
->655.417 -> 508.428
->1,525.284
->4,575.852


Final output of program is `4,575.852`.  

By rounding this value to the nearest 100, the output is `4,600`.  

`flag{4600}`  
* Nearby values (`4500`) would also be accepted, due to possibly different intermediate step rounding errors.  








