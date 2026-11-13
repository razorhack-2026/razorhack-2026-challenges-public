(* ============================================================================ *)
(* ICARUS COOLANT-LOOP INTERLOCK  --  MAINTENANCE OVERRIDE                       *)
(* RTU ladder, OpenPLC (matiec ST).  Rung: RELEASE-ON-VALID-AUTH.               *)
(*                                                                              *)
(* The coolant safety interlock will NOT lift without the maintenance           *)
(* authorization key. The key is four words, entered at AUTH0..AUTH3, and is     *)
(* checked one word at a time against the stored interlock signature SIG:        *)
(* each word is folded with the previous result, run through the RTU byte        *)
(* SCRAMBLER, then the panel's calibration constants, and compared to SIG[i].    *)
(* On a full match OVERRIDE_GRANTED latches and the sealed maintenance payload   *)
(* is unsealed to the readback registers PAYLOAD0.. using the same key.          *)
(*                                                                              *)
(* Auth key = the RTU calibration key (engineering handbook, sec. 7).           *)
(* ============================================================================ *)
PROGRAM maint_override
  VAR_EXTERNAL
    AUTH0 : WORD; AUTH1 : WORD; AUTH2 : WORD; AUTH3 : WORD;
    PAYLOAD0 : WORD; PAYLOAD1 : WORD; PAYLOAD2 : WORD; PAYLOAD3 : WORD; PAYLOAD4 : WORD; PAYLOAD5 : WORD; PAYLOAD6 : WORD; PAYLOAD7 : WORD; PAYLOAD8 : WORD; PAYLOAD9 : WORD; PAYLOAD10 : WORD; PAYLOAD11 : WORD;
    OVERRIDE_GRANTED : BOOL;
  END_VAR
  VAR CONSTANT
    (* RTU byte scrambler (fixed calibration table) *)
    SCRAMBLER : ARRAY[0..255] OF USINT := [
      203, 55, 51, 182, 30, 223, 255, 205, 69, 118, 219, 54, 127, 107, 175, 142,
      165, 38, 235, 221, 140, 112, 149, 114, 166, 139, 213, 83, 67, 89, 147, 188,
      84, 75, 242, 36, 74, 130, 144, 186, 227, 136, 2, 88, 249, 158, 195, 60,
      9, 102, 253, 32, 120, 232, 22, 14, 214, 236, 78, 160, 66, 10, 196, 91,
      222, 23, 247, 173, 53, 25, 226, 244, 96, 58, 174, 47, 250, 135, 152, 5,
      229, 59, 103, 56, 246, 41, 171, 157, 42, 146, 201, 31, 209, 71, 101, 117,
      15, 170, 191, 126, 220, 150, 192, 243, 187, 124, 26, 231, 52, 104, 64, 95,
      27, 93, 216, 217, 206, 62, 228, 45, 218, 61, 81, 49, 156, 57, 73, 19,
      85, 138, 183, 129, 34, 28, 63, 251, 148, 80, 6, 70, 254, 8, 18, 133,
      241, 113, 198, 189, 145, 50, 248, 106, 234, 123, 230, 208, 252, 181, 68, 116,
      163, 155, 99, 48, 210, 204, 1, 44, 207, 98, 200, 90, 17, 46, 178, 11,
      212, 184, 39, 215, 240, 176, 190, 7, 141, 131, 193, 137, 111, 82, 86, 169,
      180, 237, 77, 35, 72, 100, 87, 4, 12, 239, 134, 225, 43, 151, 108, 185,
      162, 224, 122, 211, 154, 76, 202, 167, 94, 20, 168, 3, 97, 143, 128, 238,
      197, 33, 0, 37, 159, 29, 119, 65, 109, 164, 153, 40, 132, 199, 161, 179,
      16, 172, 92, 121, 245, 79, 125, 115, 194, 177, 110, 105, 21, 233, 24, 13];
    (* stored interlock signature the auth key must reproduce *)
    SIG : ARRAY[0..3] OF WORD := [16#7258, 16#6DAA, 16#820C, 16#6DFA];
    (* sealed maintenance payload (unsealed only under a valid override) *)
    OVERRIDE_PAYLOAD : ARRAY[0..23] OF USINT := [
      176, 78, 97, 59, 121, 188, 67, 192, 143, 206, 130, 77, 7, 22, 16, 157,
      14, 135, 178, 102, 3, 45, 200, 159];
  END_VAR
  VAR
    tw : ARRAY[0..3] OF WORD; prevw : WORD; i : INT; t : WORD; tu : UINT;
    lo : USINT; hi : USINT; ok : BOOL;
    tb : ARRAY[0..7] OF USINT; pt : ARRAY[0..23] OF USINT; kstate : USINT; j : INT;
  END_VAR
  (* --- interlock check: fold each auth word against the stored signature --- *)
  tw[0] := AUTH0; tw[1] := AUTH1; tw[2] := AUTH2; tw[3] := AUTH3;
  prevw := 16#A5A5;                         (* interlock preload constant *)
  ok := TRUE;
  FOR i := 0 TO 3 DO
    t := tw[i] XOR prevw;                        (* chain with previous result *)
    lo := SCRAMBLER[WORD_TO_INT(t AND 16#00FF)];
    hi := SCRAMBLER[WORD_TO_INT(SHR(IN := t, N := 8) AND 16#00FF)];
    t := SHL(IN := USINT_TO_WORD(hi), N := 8) OR USINT_TO_WORD(lo);
    tu := WORD_TO_UINT(t) * UINT#141;          (* calibration multiplier *)
    t := ROL(IN := UINT_TO_WORD(tu), N := 5);
    tu := WORD_TO_UINT(t) + UINT#4660;           (* calibration offset *)
    t := UINT_TO_WORD(tu);
    IF t <> SIG[i] THEN ok := FALSE; END_IF;
    prevw := t;
  END_FOR;
  OVERRIDE_GRANTED := ok;
  IF ok THEN
    (* --- valid override: unseal the payload with a keystream from the auth key --- *)
    tb[0] := WORD_TO_USINT(SHR(IN := AUTH0, N := 8) AND 16#00FF); tb[1] := WORD_TO_USINT(AUTH0 AND 16#00FF);
    tb[2] := WORD_TO_USINT(SHR(IN := AUTH1, N := 8) AND 16#00FF); tb[3] := WORD_TO_USINT(AUTH1 AND 16#00FF);
    tb[4] := WORD_TO_USINT(SHR(IN := AUTH2, N := 8) AND 16#00FF); tb[5] := WORD_TO_USINT(AUTH2 AND 16#00FF);
    tb[6] := WORD_TO_USINT(SHR(IN := AUTH3, N := 8) AND 16#00FF); tb[7] := WORD_TO_USINT(AUTH3 AND 16#00FF);
    kstate := USINT#90;
    FOR j := 0 TO 23 DO
      kstate := SCRAMBLER[USINT_TO_INT(kstate + tb[j MOD 8] + INT_TO_USINT(j))];
      pt[j] := BYTE_TO_USINT(USINT_TO_BYTE(OVERRIDE_PAYLOAD[j]) XOR USINT_TO_BYTE(kstate));
    END_FOR;
    PAYLOAD0 := SHL(IN := USINT_TO_WORD(pt[0]), N := 8) OR USINT_TO_WORD(pt[1]);
    PAYLOAD1 := SHL(IN := USINT_TO_WORD(pt[2]), N := 8) OR USINT_TO_WORD(pt[3]);
    PAYLOAD2 := SHL(IN := USINT_TO_WORD(pt[4]), N := 8) OR USINT_TO_WORD(pt[5]);
    PAYLOAD3 := SHL(IN := USINT_TO_WORD(pt[6]), N := 8) OR USINT_TO_WORD(pt[7]);
    PAYLOAD4 := SHL(IN := USINT_TO_WORD(pt[8]), N := 8) OR USINT_TO_WORD(pt[9]);
    PAYLOAD5 := SHL(IN := USINT_TO_WORD(pt[10]), N := 8) OR USINT_TO_WORD(pt[11]);
    PAYLOAD6 := SHL(IN := USINT_TO_WORD(pt[12]), N := 8) OR USINT_TO_WORD(pt[13]);
    PAYLOAD7 := SHL(IN := USINT_TO_WORD(pt[14]), N := 8) OR USINT_TO_WORD(pt[15]);
    PAYLOAD8 := SHL(IN := USINT_TO_WORD(pt[16]), N := 8) OR USINT_TO_WORD(pt[17]);
    PAYLOAD9 := SHL(IN := USINT_TO_WORD(pt[18]), N := 8) OR USINT_TO_WORD(pt[19]);
    PAYLOAD10 := SHL(IN := USINT_TO_WORD(pt[20]), N := 8) OR USINT_TO_WORD(pt[21]);
    PAYLOAD11 := SHL(IN := USINT_TO_WORD(pt[22]), N := 8) OR USINT_TO_WORD(pt[23]);
  ELSE
    PAYLOAD0 := 16#0000;
    PAYLOAD1 := 16#0000;
    PAYLOAD2 := 16#0000;
    PAYLOAD3 := 16#0000;
    PAYLOAD4 := 16#0000;
    PAYLOAD5 := 16#0000;
    PAYLOAD6 := 16#0000;
    PAYLOAD7 := 16#0000;
    PAYLOAD8 := 16#0000;
    PAYLOAD9 := 16#0000;
    PAYLOAD10 := 16#0000;
    PAYLOAD11 := 16#0000;
  END_IF;
END_PROGRAM

CONFIGURATION Config0
  VAR_GLOBAL
    (* AUTH = maintenance auth key (holding regs, operator-writable) *)
    AUTH0 AT %QW0 : WORD; AUTH1 AT %QW1 : WORD; AUTH2 AT %QW2 : WORD; AUTH3 AT %QW3 : WORD;
    (* PAYLOAD = maintenance payload readback *)
    PAYLOAD0 AT %QW10 : WORD;
    PAYLOAD1 AT %QW11 : WORD;
    PAYLOAD2 AT %QW12 : WORD;
    PAYLOAD3 AT %QW13 : WORD;
    PAYLOAD4 AT %QW14 : WORD;
    PAYLOAD5 AT %QW15 : WORD;
    PAYLOAD6 AT %QW16 : WORD;
    PAYLOAD7 AT %QW17 : WORD;
    PAYLOAD8 AT %QW18 : WORD;
    PAYLOAD9 AT %QW19 : WORD;
    PAYLOAD10 AT %QW20 : WORD;
    PAYLOAD11 AT %QW21 : WORD;
    OVERRIDE_GRANTED AT %QX0.0 : BOOL;
  END_VAR
  RESOURCE Res0 ON PLC
    TASK Main(INTERVAL := T#50ms, PRIORITY := 0);
    PROGRAM Inst0 WITH Main : maint_override;
  END_RESOURCE
END_CONFIGURATION
