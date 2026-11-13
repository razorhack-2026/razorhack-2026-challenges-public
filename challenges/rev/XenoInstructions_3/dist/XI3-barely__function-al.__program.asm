Filename:  
`XI3-barely__function-al.__program.asm`  

```
BEGIN PROGRAM


.instructions:
Null Un Bin Tern Un Un Bin Quatern Bin Null


.to_run_per_instruc:
_ -> [.instruc_opcode_lut] -> [.fun] -> SYS_OUT_PRINT


.instruc_opcode_lut:
Null 0
Un 1
Bin 2
Tern 3
Quat 4
Quatern 4
Pent 5
Penten 5
Sexen 6
Hep 7


.fun:

a,b,c,d,e,f,g -> HALT_PROGRAM

z,a,b,c,x,y -> z*a+z*b+z*c-z*x-z*y-z

a,b,c,d,e -> ENTER_OVERCLOCK_MODE

a,b,c,d -> a*b/c-d

a,x,z -> z+a+x*log(x)

d,f -> sqrt(d+d*f)

e -> e+e+e

ABSENCE -> STARTNUM


.unit_test_assertion
5,4,2,0 -> 10
5,4,2,1 -> 20
5,4,2,2 -> TRAP_PROGRAM_FATAL
0,0,0 -> TRAP_PROGRAM_FATAL
5,-5 -> 7.071i
5,-6 -> 7.746i
-0.5,49 -> 7i
-1,2 -> 2i
0,0 -> 0
5 -> 15
0 -> 0


.const:
STARTNUM 42
ABSENCE:bytesQuantity (push +0[0])


.comment:
Section__to_run_per_instruc__must_begin_with_underscore_to_imply_arbitrary_input;
;
LUT_is_LookUpTable;
;
AnonymousFunctions_doNot_have_names;
;
Each_numeric_opcode_value_is_allowed_to_have_multiple_aliases_for_programmer_convenience_when_writing_instructions;
;
LogOfX_is_assumed_to_be_LogBase10_not_LogBase2_nor_LogBase_e;
;
Beware_of_OrderOfOperations;
;
Beware_of_ParameterOrdering;
;
I_Wonder_If_More_Than_Just_LTR_and_PEMDAS_Exist;
;
This_ISA_Supports_ComplexNumbers_of_Form_A+Bi__where_A_isRealPart_and_B_isImaginaryPart__example_15.3-5i;


END PROGRAM
```