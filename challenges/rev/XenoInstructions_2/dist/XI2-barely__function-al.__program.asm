Filename:  
`XI2-barely__function-al.__program.asm`  

```
BEGIN PROGRAM


.instructions:
Null Un Bin Tern Un Un Bin Quatern Bin


.to_run_per_instruc:
_ -> [.instruc_opcode_lut] -> [.fun] -> SYS_OUT_PRINT


.instruc_opcode_lut:
Null 0
Un 1
Bin 2
Tern 3
Quat 4
Quatern 4


.fun:
CORRUPTED -> a+b+c+d

CORRUPTED -> z+a+x*log(x)

CORRUPTED -> sqrt(d+d*f)

CORRUPTED -> e+e+e

CORRUPTED -> STARTNUM


.unit_test_assertion
1,2,3,4 -> 10
0,1,1,0 -> 2
0,0,1000 -> 3000
0,0,100 -> 200
0,0,10 -> 10
0,0,1 -> 0
0,0,0 -> TRAP_PROGRAM_FATAL
5,-5 -> 7.071i
5,5 -> 7.071
2,2 -> 2.828
5 -> 15
0 -> 0


.const:
STARTNUM 42


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
This_ISA_Supports_ComplexNumbers_of_Form_A+Bi__where_A_isRealPart_and_B_isImaginaryPart__example_15.3-5i;


END PROGRAM
```