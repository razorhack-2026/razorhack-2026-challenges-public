(* Student copy of the Training Bay PLC logic. Secret constants are
   redacted. Use it to work out WHAT the PLC wants; the register map
   tells you WHERE to write it. *)

(* =====================================================================
   RazorHack Training Bay - PLC logic for the OpenPLC/Modbus warm-ups
   ISV Ozark Horizon training rig

   Each challenge is one small function block using standard IEC timers
   and counters (TON, CTU, R_TRIG), the same blocks you will meet in
   OpenPLC ladder logic. PROGRAM prog0 (separate file) wires them to
   Modbus addresses and handles the "reset for the next team" outputs.

   Every success holds for a 20 s window, then the block re-arms so the
   next team on a shared rig has to do the work themselves.
   ===================================================================== *)

(* ---------------------------------------------------------------------
   MB4 - Beacon. A plain command coil. The PLC turns it back off after
   15 s so the beacon is not left lit for everyone.
   --------------------------------------------------------------------- *)
FUNCTION_BLOCK FB_Beacon
VAR_INPUT
    Beacon_On : BOOL;
END_VAR
VAR_OUTPUT
    Lit      : BOOL;
    Auto_Off : BOOL;      (* TRUE -> program clears the coil *)
END_VAR
VAR
    on_tmr : TON;
END_VAR
on_tmr(IN := Beacon_On, PT := T#15s);
Lit      := Beacon_On;
Auto_Off := on_tmr.Q;
END_FUNCTION_BLOCK

(* ---------------------------------------------------------------------
   PL1 - Airlock interlock. The outer door may open only when:
     * the inner door is closed AND the suit check passed,
     * the chamber has been pumped down (4 s with both of the above), and
     * nobody has the maintenance override engaged,
     * and a cycle is requested.
   --------------------------------------------------------------------- *)
FUNCTION_BLOCK FB_Airlock
VAR_INPUT
    Inner_Closed : BOOL;
    Suit_Ok      : BOOL;
    Override     : BOOL;
    Cycle_Req    : BOOL;
END_VAR
VAR_OUTPUT
    Depressurized : BOOL;
    Door_Open     : BOOL;
    Reset_Cycle   : BOOL;   (* TRUE -> program re-arms the airlock *)
END_VAR
VAR
    pump     : TON;
    open_tmr : TON;
END_VAR
pump(IN := Inner_Closed AND Suit_Ok, PT := T#4s);
Depressurized := pump.Q;

Door_Open := Cycle_Req AND Inner_Closed AND Suit_Ok
             AND Depressurized AND NOT Override;

open_tmr(IN := Door_Open, PT := T#20s);
Reset_Cycle := open_tmr.Q;
END_FUNCTION_BLOCK

(* ---------------------------------------------------------------------
   PL2 - Hold-to-confirm. The confirm button must be held continuously
   for 5 s. Letting go early restarts the timer (that is what TON does).
   --------------------------------------------------------------------- *)
FUNCTION_BLOCK FB_HoldTimer
VAR_INPUT
    Hold_Btn : BOOL;
END_VAR
VAR_OUTPUT
    Done        : BOOL;
    Elapsed_ds  : INT;     (* tenths of a second the button has been held *)
    Release_Btn : BOOL;    (* TRUE -> program releases the button *)
END_VAR
VAR
    hold_tmr : TON;
    win      : TON;
    latched  : BOOL;
END_VAR
hold_tmr(IN := Hold_Btn, PT := T#5s);
Elapsed_ds := DINT_TO_INT(TIME_TO_DINT(hold_tmr.ET) / 100);
IF hold_tmr.Q THEN
    latched := TRUE;
END_IF;
win(IN := latched, PT := T#20s);
IF win.Q THEN
    latched := FALSE;
END_IF;
Done        := latched;
Release_Btn := hold_tmr.Q;
END_FUNCTION_BLOCK

(* ---------------------------------------------------------------------
   PL3 - Pulse counter. Count exactly 7 rising edges on the pulse input,
   then leave the input OFF for 2 s to confirm. An 8th pulse is a fault
   that only the reset input clears. R_TRIG means holding the input ON
   counts once - and an ON/OFF that happens between two PLC scans is
   never seen at all.
   --------------------------------------------------------------------- *)
FUNCTION_BLOCK FB_PulseCounter
VAR_INPUT
    Pulse_In    : BOOL;
    Count_Reset : BOOL;
END_VAR
VAR_OUTPUT
    Count       : INT;
    Fault       : BOOL;
    Done        : BOOL;
    Clear_Reset : BOOL;    (* TRUE -> program releases the reset input *)
END_VAR
VAR
    edge    : R_TRIG;
    ctr     : CTU;
    settle  : TON;
    win     : TON;
    latched : BOOL;
END_VAR
edge(CLK := Pulse_In);
(* CTU stops counting once CV reaches PV, so PV is set well above the
   target - otherwise an 8th pulse would simply be ignored. CTU also
   edge-detects internally; the explicit R_TRIG is here so you can see it. *)
ctr(CU := edge.Q, R := Count_Reset OR win.Q, PV := 99);
Count := ctr.CV;
Fault := ctr.CV > 7;

settle(IN := (ctr.CV = 7) AND NOT Pulse_In, PT := T#2s);
IF settle.Q THEN
    latched := TRUE;
END_IF;
win(IN := latched, PT := T#20s);
IF win.Q THEN
    latched := FALSE;
END_IF;
Done        := latched;
Clear_Reset := Count_Reset;
END_FUNCTION_BLOCK

(* ---------------------------------------------------------------------
   PL4 - Three-wire motor starter (seal-in / latch).
   START is a momentary, normally-open button.
   STOP is a normally-CLOSED button: the PLC input is TRUE while STOP is
   NOT pressed, and FALSE when it is pressed (or the wire is cut).
   Success = motor running on its own seal-in with START released, 3 s.
   --------------------------------------------------------------------- *)
FUNCTION_BLOCK FB_MotorSealIn
VAR_INPUT
    Start_PB   : BOOL;
    Stop_PB_NC : BOOL;
END_VAR
VAR_OUTPUT
    Motor_Run   : BOOL;
    Done        : BOOL;
    Reset_Panel : BOOL;    (* TRUE -> program resets START/STOP inputs *)
END_VAR
VAR
    run_tmr : TON;
    win     : TON;
    latched : BOOL;
END_VAR
Motor_Run := (Start_PB OR Motor_Run) AND Stop_PB_NC;

run_tmr(IN := Motor_Run AND NOT Start_PB, PT := T#3s);
IF run_tmr.Q THEN
    latched := TRUE;
END_IF;
win(IN := latched, PT := T#20s);
Reset_Panel := win.Q;
IF win.Q THEN
    latched   := FALSE;
    Motor_Run := FALSE;
END_IF;
Done := latched;
END_FUNCTION_BLOCK

(* ---------------------------------------------------------------------
   PL5 - 4-20 mA analog scaling. The ADC reports 4 mA as raw 6554 and
   20 mA as raw 32767. Engineering value is 0-100 % (reported x10).
   Below ~3.9 mA the loop is treated as a broken wire.
   Success = tank level held at 62.5 % (+/- 0.1) for 2 s.
   --------------------------------------------------------------------- *)
FUNCTION_BLOCK FB_Scaling
VAR_INPUT
    Raw : INT;
END_VAR
VAR_OUTPUT
    Eng_x10    : INT;      (* percent x10, -1 = wire break *)
    Wire_Break : BOOL;
    Done       : BOOL;
    Clear_Raw  : BOOL;     (* TRUE -> program zeroes the raw input *)
END_VAR
VAR CONSTANT
    RAW_4MA  : REAL := 6554.0;
    RAW_20MA : REAL := 32767.0;
END_VAR
VAR
    eng     : REAL;
    on_tgt  : TON;
    win     : TON;
    latched : BOOL;
END_VAR
Wire_Break := Raw < 6400;
IF Wire_Break THEN
    Eng_x10 := -1;
ELSE
    eng := (INT_TO_REAL(Raw) - RAW_4MA) / (RAW_20MA - RAW_4MA) * 100.0;
    Eng_x10 := REAL_TO_INT(eng * 10.0);
END_IF;

on_tgt(IN := NOT Wire_Break AND Eng_x10 >= 624 AND Eng_x10 <= 626, PT := T#2s);
IF on_tgt.Q THEN
    latched := TRUE;
END_IF;
win(IN := latched, PT := T#20s);
IF win.Q THEN
    latched := FALSE;
END_IF;
Done      := latched;
Clear_Raw := win.Q;
END_FUNCTION_BLOCK

(* ---------------------------------------------------------------------
   MB7 - Breaker panel. One 16-bit register holds 16 breaker bits.
   Close ONE breaker (bit 9) and leave every other bit exactly
   as it was. Any other change trips the panel; only the reset coil
   clears a trip.
   --------------------------------------------------------------------- *)
FUNCTION_BLOCK FB_BreakerPanel
VAR_INPUT
    Word      : INT;
    Reset_Cmd : BOOL;
END_VAR
VAR_OUTPUT
    Tripped     : BOOL;
    Done        : BOOL;
    Restore     : BOOL;    (* TRUE -> program writes the initial pattern back *)
    Clear_Reset : BOOL;    (* TRUE -> program releases the reset coil *)
END_VAR
VAR CONSTANT
    INIT_WORD : INT := 16#????  (* REDACTED - read the live panel *);
    GOAL_WORD : INT := 16#????  (* REDACTED *);
END_VAR
VAR
    win     : TON;
    latched : BOOL;
END_VAR
Restore := FALSE;
IF Reset_Cmd THEN
    Tripped := FALSE;
    latched := FALSE;
    Restore := TRUE;
ELSIF NOT Tripped AND NOT latched THEN
    IF Word = GOAL_WORD THEN
        latched := TRUE;
    ELSIF Word <> INIT_WORD THEN
        Tripped := TRUE;
    END_IF;
END_IF;

win(IN := latched, PT := T#20s);
IF win.Q THEN
    latched := FALSE;
    Restore := TRUE;
END_IF;
Done        := latched;
Clear_Reset := Reset_Cmd;
END_FUNCTION_BLOCK

(* ---------------------------------------------------------------------
   IG3 - Beacon tuner (driven from the Ignition HMI). The frequency is
   cleared 30 s after it is tuned correctly.
   --------------------------------------------------------------------- *)
FUNCTION_BLOCK FB_Tuner
VAR_INPUT
    Freq : INT;
END_VAR
VAR_OUTPUT
    Locked     : BOOL;
    Clear_Freq : BOOL;     (* TRUE -> program zeroes the frequency *)
END_VAR
VAR CONSTANT
    TARGET : INT := ????  (* REDACTED - see the HMI *);
END_VAR
VAR
    on_tmr : TON;
END_VAR
Locked := Freq = TARGET;
on_tmr(IN := Locked, PT := T#30s);
Clear_Freq := on_tmr.Q;
END_FUNCTION_BLOCK
