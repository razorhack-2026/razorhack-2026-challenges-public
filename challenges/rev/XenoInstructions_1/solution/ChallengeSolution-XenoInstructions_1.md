## ChallengeName  
XenoInstructions #1  

**Category:**    Rev (Reverse Engineering)  
**Difficulty:**  medium  
**Author:**      "Mort (StevieoXOR)"  


### ChallengeDescription_Themed_ViewableByParticipant  
A program that resembles Assembly, coded in a Functional Paradigm, was found. However, it seems a logical block that defines functions was partially corrupted. Can you recover and run the fixed program? You should wrap the program's final output value (do not include any intermediary computations) in "flag{" and "}".  

### FilesProvidedToParticipant  
* dist/XI1-barely__function-al.__program.asm  

### Flags that participant can submit  
* flag{42}  





# Solution  


## TL;DR  

* The final output of the program is the result of calling the nullary function, so only the very last instruction *needs* to be executed. The flag is the result of calling the nullary function, then wrapping that integer in `flag{` and `}`.  



## FullSolution Explanation  

0-ary/nullary, unary, binary, ternary, unary, unary, binary, quaternary, binary, null  
* Each of these corresponds to the **quantity** of arguments expected to be provided as input.  

# Explanation of the set of functions  
```
.fun:
CORRUPTED -> a+b+c+d
// ^^^ Has a,b,c,d:	4 unique inputs -> is a quaternary function

CORRUPTED -> z+a+x^x
// ^^^ Has z,a,x:	3 unique inputs -> is a ternary function
// ^^^ Just because the ordering of the inputs is z,a,x, rather than a,x,z, makes no difference. Inputs are still interpreted as left-to-right.

CORRUPTED -> sqrt(d+d*f)
// ^^^ Has d,f:		2 unique inputs -> is a binary function

CORRUPTED -> e+e+e
// ^^^ Has e:		1 unique input -> is a unary function

CORRUPTED -> STARTNUM
// ^^^ Has nothing:	0 unique inputs -> is a nullary function
```

Notice how there are not *multiple* functions that happen to take the same # of arguments.  
* I.e., the following doesn't appear in the program at the same time:  
  * CORRUPTED -> e+e+e	// Unary  
  * CORRUPTED -> a+a+a	// [WARNING] AMBIGUOUS: UNARY FUNCTION ALREADY DEFINED  

Each function outputs a SINGLE value, not two or three or four values.  
* So, how does the code executor know how to deal with any function other than a unary function?  
* I decided to make it where `Null Un Bin Tern Un` searches in the following order:  
  * Un looks at Null  
  * Bin looks at Un, and then Null  
  * Tern looks at Bin, and then Un, and then Null  
  * The very last (i.e., rightmost) Un will look at its previous instruction for obtaining an input value, which happens to be Tern.  
  * The very last instruction is Null, which does NOT take any inputs. Therefore, the last instruction does NOT depend on any of the program's previous instructions, meaning the program's final result is independent of ALL the program's other instructions.  



The square brackets [...] serve as a "goto"/"dereference" operator.  

Each block of text that (begins with a ".", followed by a word that contains no space-like characters) is a "section" of code/text that can be navigated to (by wrapping that label in square brackets).  

The ".comment" section indicates to be aware of OrderOfOperations. There are two typical OOO conventions:  
* left-to-right  
* PEMDAS (Parentheses, Exponents, Multiplication&Division_Equally, Addition&Subtraction_Equally)  

You might need to try each OOO definition, if the flag you get after computing ends up being wrong.  
* This challenge uses LTR first, and when LTR can't reasonably apply (e.g., function calls), then PEMDAS (specifically the Parentheses part) takes over.  






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

(STARTNUM)->(e+e+e)->(sqrt(d+d*f))->(z+a+x^x)->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))->(STARTNUM)  

==  
42->(e+e+e)->(sqrt(d+d*f))->(z+a+x^x)->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))->42  

==  
42->(42+42+42)->(sqrt(d+d*f))->(z+a+x^x)->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))->42  


==  
42 =================V  
->(42+42+42)        e     // Refers to previous func's result  
->(sqrt(d+d*f))	 
->(z+a+x^x)  
->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))->42  


==  
42 ======================================\  
->(42+42+42)    ================\         |  
                                 V        V  
->(sqrt(42+42*(42+42+42)))	 d=42     f=(42+42+42) (note: d then f, NOT f then d. Leftmost parameter is most recently called func's result.)  
->(z+a+x^x)  
->(e+e+e)  
->(e+e+e)  
->(sqrt(d+d*f))  
->(a+b+c+d)  
->(sqrt(d+d*f))  
->42  

==  
42    ===================================================================\  
->(42+42+42)  ---------------------------------------------\              \  
->(sqrt(42+42*(42+42+42))) ====\                            V              V  
->(z+a+x^x)                     z=sqrt(42+42*(42+42+42))    a=(42+42+42)   x=42  
->(e+e+e)  
->(e+e+e)  
->(sqrt(d+d*f))  
->(a+b+c+d)  
->(sqrt(d+d*f))  
->42  


==  
42    ==============================================================================================\  
->(42+42+42)  ------------------------------------------------------------------------\              \  
->(sqrt(42+42*(42+42+42))) ================================\                           V              V  
->( sqrt(42+42*(42+42+42)) + (42+42+42) + 42^42 )           z=sqrt(42+42*(42+42+42))   a=(42+42+42)   x=42   (Leftmost parameter is most recently called func's result.)  
->(e+e+e)  
->(e+e+e)  
->(sqrt(d+d*f))  
->(a+b+c+d)  
->(sqrt(d+d*f))  
->42  


==  
42  
->(42+42+42)  
->(sqrt(42+42*(42+42+42)))  
->( sqrt(42+42*(42+42+42)) + (42+42+42) + 42^42 )    ========V  
->(                                                          e=( sqrt(42+42*(42+42+42)) + (42+42+42) + 42^42 )  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42^42 )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42^42 )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42^42 )  
)  
->(e+e+e)  
->(sqrt(d+d*f))  
->(a+b+c+d)  
->(sqrt(d+d*f))  
->42  


==  
Doesn'tMatter  
-> Doesn'tMatter  
-> Doesn'tMatter  
-> Doesn'tMatter  
-> Doesn'tMatter  
-> Doesn'tMatter  
-> Doesn'tMatter  
-> Doesn'tMatter  
-> Doesn'tMatter  
-> 42  

(The nullary function takes no input, so all instructions that come before the call of the nullary function are irrelevant).

Result of program = 42  

Submission: `flag{42}`  

