
ChallengeSolution-XenoInstructions_2.md
-------------



## ChallengeName  
XenoInstructions #2  

**Category:**    Rev (Reverse Engineering)  
**Difficulty:**  hard  
**Author:**      "Mort (StevieoXOR)"  

### ChallengeDescription_Themed_ViewableByParticipant  
A program that resembles Assembly, coded in a Functional Paradigm, was found. However, it seems a logical block that defines functions was partially corrupted. Can you recover and run the fixed program? You should round the program's final output value (do not include any intermediary computations) to the nearest 100 (either with comma or without are both okay), and then wrap that rounded value in the text "flag{" and "}".  

### FilesProvidedToParticipant  
* dist/XI2-barely__function-al.__program.asm  

### Flags that participant can submit  
* flag{7,603.960}  
* flag{7,603}  
* flag{7,604}  
* flag{7,600}  
* flag{7,700}  
* flag{7600}  
* flag{7700}  


Depending on how the participant rounds numbers in the intermediate steps, the final result could vary a lot.  
So, I'm allowing answers to be anywhere from 25,000 to 30,000.  




# Solution  


## TL;DR  

* Unlike XenoInstructions #1, ALL the instructions will need to be executed, not just the very last instruction.  
* The final output of the program is the result of calling all the instructions, calling them one-by-one from left to right ("LTR").  
* The flag is that final output of the program, after wrapping that integer in `flag{` and `}`.  



# Solution  


## FullSolution Explanation  

0-ary/nullary, unary, binary, ternary, unary, unary, binary, quaternary, binary, null  
* Each of these corresponds to the **quantity** of arguments expected to be provided as input.  

# Explanation of the set of functions  
```
.fun:
CORRUPTED -> a+b+c+d
// ^^^ Has a,b,c,d:	4 unique inputs -> is a quaternary function

CORRUPTED -> z+a+x*log(x)
// ^^^ Has z,a,x:	3 unique inputs -> is a ternary function
// ^^^ Just because the ordering of the inputs is z,a,x, rather than a,x,z, makes no difference. Inputs are still interpreted as left-to-right.
// ^^^ log(x) is assumed to be "log Base10 (of x)", not "log BaseE" nor "log Base2".

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
  * The very first instruction is Null, which does NOT take any inputs. Therefore, the first instruction does NOT depend on any of the program's previous instructions, meaning the program's first step is independent of ALL the program's other instructions.  



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
Null Un Bin Tern Un Un Bin Quatern Bin  

==  
0 1 2 3 1  1 2 4 2  

== (after identifying the functions that correspond to the digits above)  

(STARTNUM)->(e+e+e)->(sqrt(d+d*f))->(z+a+x*log(x))->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  

==  
42->(e+e+e)->(sqrt(d+d*f))->(z+a+x*log(x))->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  

==  
42->(42+42+42)->(sqrt(d+d*f))->(z+a+x*log(x))->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  


==  
42 =================V  
->(42+42+42)        e     // Refers to previous func's result  
->(sqrt(d+d*f))	 
->(z+a+x*log(x))  
->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  


==  
42 ======================================\  
->(42+42+42)    ================\         |  
                                 V        V  
->(sqrt(42+42*(42+42+42)))	 d=42     f=(42+42+42) (note: d then f, NOT f then d. Leftmost parameter is most recently called func's result.)  
->(z+a+x*log(x))  
->(e+e+e)  
->(e+e+e)  
->(sqrt(d+d*f))  
->(a+b+c+d)  
->(sqrt(d+d*f))  

==  
42    ===================================================================\  
->(42+42+42)  ---------------------------------------------\              \  
->(sqrt(42+42*(42+42+42))) ====\                            V              V  
->(z+a+x*log(x))                     z=sqrt(42+42*(42+42+42))    a=(42+42+42)   x=42  
->(e+e+e)  
->(e+e+e)  
->(sqrt(d+d*f))  
->(a+b+c+d)  
->(sqrt(d+d*f))  


==  
42    ==============================================================================================\  
->(42+42+42)  ------------------------------------------------------------------------\              \  
->(sqrt(42+42*(42+42+42))) ================================\                           V              V  
->( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )      z=sqrt(42+42*(42+42+42))   a=(42+42+42)   x=42   (Leftmost parameter is most recently called func's result.)  
->(e+e+e)  
->(e+e+e)  
->(sqrt(d+d*f))  
->(a+b+c+d)  
->(sqrt(d+d*f))  


==  
42  
->(42+42+42)  
->(sqrt(42+42*(42+42+42)))  
->( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )    ========V  
->(                                                               e=( sqrt(42+42*(42+42+42)) + (42+42+42) + 42^42 )  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  
->(e+e+e)  
->(sqrt(d+d*f))  
->(a+b+c+d)  
->(sqrt(d+d*f))  






==  

42  
->(42+42+42)  
->(sqrt(42+42*(42+42+42)))  
->( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  

->  
e="3 of most recent func call, each copy accumulating (i.e., summed)":  
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  


->
e="3 of most recent func call, each copy accumulating (i.e., summed)"
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  
+  
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  

+  
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  


->  
(sqrt(d+d*f))	// d="Most recent func call",  f="2nd most recent func call"  

->(a+b+c+d)  
->(sqrt(d+d*f))  








==  

42  
->(42+42+42)  
->(sqrt(42+42*(42+42+42)))  
->( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  

->  
e="3 of most recent func call, each copy accumulating (i.e., summed)":  
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  


->
e="3 of most recent func call, each copy accumulating (i.e., summed)"
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  
+  
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  

+  
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  


->  
(sqrt(d+d*f))	// d="Most recent func call",  f="2nd most recent func call"
d:
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  
+  
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  

+  
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  
+
d:
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  
+  
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  

+  
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  
*
f:
(  
    ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
  + ( sqrt(42+42*(42+42+42)) + (42+42+42) + 42*log(42) )  
)  



->(a+b+c+d)  
->(sqrt(d+d*f))  




Okay, this is taking up too way much space to keep it generalizable, so, going back a bunch of steps:  

==  
42->(42+42+42)->(sqrt(d+d*f))->(z+a+x*log(x))->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  

==  
42->126->(sqrt(d+d*f))->(z+a+x*log(x))->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  

==  
42->126->(sqrt(126+126*42))->(z+a+x*log(x))->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  

Now, unlike with the unambiguous substitutions made earlier, now there's a choice to make:  
* Perform arithmetic LeftToRight vs PEMDAS  

I choose LTR for the fundamental operations like +,-,*,/, but the more complicated operations like sqrt() and log() will happen according to parentheses-based ordering.  
* In the case of this program, that means that sqrt() will happen last (within the instruction that contains a sqrt() operation).  


==  
42->126->(sqrt(252*42))->(z+a+x*log(x))->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  


==  
42->126->(sqrt(10,584))->(z+a+x*log(x))->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  

Now, there's another choice to make:
* Perform integer truncation after the square root, or preserve a few digits of precision after the decimal point, or preserve 32-bit float precision, or preserve 64-bit double precision?  

I choose three digits of precision, as that's reasonable to do by hand calculator while sticking somewhat close to a typical programming language's return type of the `sqrt` operation.  


==  
42  
->126  
->102.879  
->(z+a+x*log(x))  
->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->(102.879+126+42*log(42))  
->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->(228.879+42*log(42))  
->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->(270.879*log(42))  
->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->439.704  
->(e+e+e)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->439.704  
->(439.704 + 439.704 + 439.704)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->439.704  
->(3 * 439.704)  
->(e+e+e)->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->439.704  
->1,319.112  
->(e+e+e)  
->(sqrt(d+d*f))->(a+b+c+d)->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->439.704  
->1,319.112  
->(1,319.112 + 1,319.112 + 1,319.112)  
->(sqrt(d+d*f))  
->(a+b+c+d)  
->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->439.704  
->1,319.112  
->(3 * 1,319.112)  
->(sqrt(d+d*f))  
->(a+b+c+d)  
->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->439.704  
->1,319.112  
->3,957.337  
->(sqrt(d+d*f))  
->(a+b+c+d)  
->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->439.704  
->1,319.112  
->3,957.337  
->(sqrt(3,957.337 + 3,957.337 * 1,319.112))  
->(a+b+c+d)  
->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->439.704  
->1,319.112  
->3,957.337  
->(sqrt(7,914.675 * 1,319.112))  
->(a+b+c+d)  
->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->439.704  
->1,319.112  
->3,957.337  
->(sqrt(10,440,342.243))  
->(a+b+c+d)  
->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->439.704  
->1,319.112  
->3,957.337  
->3,231.152  
->(a+b+c+d)  
->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->439.704  
->1,319.112  
->3,957.337  
->3,231.152  
->(3,231.152 + 3,957.337 + 1,319.112 + 439.704)  
->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->439.704  
->1,319.112  
->3,957.337  
->3,231.152  
->8,947.305  
->(sqrt(d+d*f))  


==  
42  
->126  
->102.879  
->439.704  
->1,319.112  
->3,957.337  
->3,231.152  
->8,947.305  
->(sqrt(8,947.305 + 8,947.305 * 3,231.152))  


==  
42  
->126  
->102.879  
->439.704  
->1,319.112  
->3,957.337  
->3,231.152  
->8,947.305  
->(sqrt(17,894.610 * 3,231.152))  


==  
42  
->126  
->102.879  
->439.704  
->1,319.112  
->3,957.337  
->3,231.152  
->8,947.305  
->(sqrt(57,820,203.887))  


==  
42  
->126  
->102.879  
->439.704  
->1,319.112  
->3,957.337  
->3,231.152  
->8,947.305  
->7,603.960  





Final result of program:  
* Roughly 7,603.960 (assuming the participant rounded the values in intermediate steps to three places every time)












