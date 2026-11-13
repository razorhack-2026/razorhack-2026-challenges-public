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
    INIT_WORD : INT := 26901;
    GOAL_WORD : INT := 27413;
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
    TARGET : INT := 1420;
END_VAR
VAR
    on_tmr : TON;
END_VAR
Locked := Freq = TARGET;
on_tmr(IN := Locked, PT := T#30s);
Clear_Freq := on_tmr.Q;
END_FUNCTION_BLOCK


(* =====================================================================
   PROGRAM prog0 - Training Bay wiring
   Located variables -> Modbus (OpenPLC v4 modbus_slave plugin):
     %QW n    -> holding register n             (read-only to players)
     %MW n    -> holding register 1024 + n      (player-writable)
     %QX a.b  -> coil 8*a + b                   (player-writable)
   GENERATED FROM TEMPLATE - edit the .tmpl and rebuild
   ===================================================================== *)
PROGRAM prog0
VAR
    beacon   : FB_Beacon;
    airlock  : FB_Airlock;
    holdt    : FB_HoldTimer;
    pulses   : FB_PulseCounter;
    motor    : FB_MotorSealIn;
    scaler   : FB_Scaling;
    breakers : FB_BreakerPanel;
    tuner    : FB_Tuner;
    firstScan : BOOL := TRUE;
    unlock    : INT;

    (* ---- player coils ---- *)
    Beacon_On     AT %QX0.0 : BOOL;   (* coil 0  *)
    Inner_Closed  AT %QX1.0 : BOOL;   (* coil 8  *)
    Suit_Ok       AT %QX1.1 : BOOL;   (* coil 9  *)
    Override      AT %QX1.2 : BOOL;   (* coil 10 *)
    Cycle_Req     AT %QX1.3 : BOOL;   (* coil 11 *)
    Hold_Btn      AT %QX2.0 : BOOL;   (* coil 16 *)
    Pulse_In      AT %QX2.1 : BOOL;   (* coil 17 *)
    Count_Reset   AT %QX2.2 : BOOL;   (* coil 18 *)
    Start_PB      AT %QX3.0 : BOOL;   (* coil 24 *)
    Stop_PB_NC    AT %QX3.1 : BOOL;   (* coil 25 *)
    Breaker_Reset AT %QX3.6 : BOOL;   (* coil 30 *)

    (* ---- player-writable registers (HR 1024+) ---- *)
    Analog_Raw    AT %MW0 : INT;      (* HR 1024 *)
    Breaker_Word  AT %MW1 : INT;      (* HR 1025 *)
    Beacon_Freq   AT %MW2 : INT;      (* HR 1026 *)

    (* ---- read-only registers ---- *)
    Bay_Id        AT %QW0   : INT;
    Heartbeat     AT %QW1   : INT;
    Big_Hi        AT %QW400 : INT;
    Big_Lo        AT %QW401 : INT;
    Flt_Hi        AT %QW410 : INT;
    Flt_Lo        AT %QW411 : INT;
    Diag_Count    AT %QW730 : INT;
    Diag_Hold     AT %QW731 : INT;
    Diag_Motor    AT %QW732 : INT;
    Diag_Eng      AT %QW733 : INT;
    Diag_Door     AT %QW734 : INT;
    Diag_Trip     AT %QW735 : INT;
    Diag_Chamber  AT %QW736 : INT;
    Diag_Fault    AT %QW737 : INT;
    IG3_Locked    AT %QW740 : INT;
    Unlock_Word   AT %QW745 : INT;

    (* ---- flag text blocks ---- *)
    F_mb2_00 AT %QW10 : INT;
    F_mb2_01 AT %QW11 : INT;
    F_mb2_02 AT %QW12 : INT;
    F_mb2_03 AT %QW13 : INT;
    F_mb2_04 AT %QW14 : INT;
    F_mb2_05 AT %QW15 : INT;
    F_mb2_06 AT %QW16 : INT;
    F_mb2_07 AT %QW17 : INT;
    F_mb2_08 AT %QW18 : INT;
    F_mb2_09 AT %QW19 : INT;
    F_mb2_10 AT %QW20 : INT;
    F_mb2_11 AT %QW21 : INT;
    F_mb2_12 AT %QW22 : INT;
    F_mb2_13 AT %QW23 : INT;
    F_mb2_14 AT %QW24 : INT;
    F_mb2_15 AT %QW25 : INT;
    F_mb3_00 AT %QW200 : INT;
    F_mb3_01 AT %QW201 : INT;
    F_mb3_02 AT %QW202 : INT;
    F_mb3_03 AT %QW203 : INT;
    F_mb3_04 AT %QW204 : INT;
    F_mb3_05 AT %QW205 : INT;
    F_mb3_06 AT %QW206 : INT;
    F_mb3_07 AT %QW207 : INT;
    F_mb3_08 AT %QW208 : INT;
    F_mb3_09 AT %QW209 : INT;
    F_mb3_10 AT %QW210 : INT;
    F_mb3_11 AT %QW211 : INT;
    F_mb3_12 AT %QW212 : INT;
    F_mb3_13 AT %QW213 : INT;
    F_mb3_14 AT %QW214 : INT;
    F_mb3_15 AT %QW215 : INT;
    F_mb4_00 AT %QW300 : INT;
    F_mb4_01 AT %QW301 : INT;
    F_mb4_02 AT %QW302 : INT;
    F_mb4_03 AT %QW303 : INT;
    F_mb4_04 AT %QW304 : INT;
    F_mb4_05 AT %QW305 : INT;
    F_mb4_06 AT %QW306 : INT;
    F_mb4_07 AT %QW307 : INT;
    F_mb4_08 AT %QW308 : INT;
    F_mb4_09 AT %QW309 : INT;
    F_mb4_10 AT %QW310 : INT;
    F_mb4_11 AT %QW311 : INT;
    F_mb4_12 AT %QW312 : INT;
    F_mb4_13 AT %QW313 : INT;
    F_mb4_14 AT %QW314 : INT;
    F_mb4_15 AT %QW315 : INT;
    F_pl1_00 AT %QW600 : INT;
    F_pl1_01 AT %QW601 : INT;
    F_pl1_02 AT %QW602 : INT;
    F_pl1_03 AT %QW603 : INT;
    F_pl1_04 AT %QW604 : INT;
    F_pl1_05 AT %QW605 : INT;
    F_pl1_06 AT %QW606 : INT;
    F_pl1_07 AT %QW607 : INT;
    F_pl1_08 AT %QW608 : INT;
    F_pl1_09 AT %QW609 : INT;
    F_pl1_10 AT %QW610 : INT;
    F_pl1_11 AT %QW611 : INT;
    F_pl1_12 AT %QW612 : INT;
    F_pl1_13 AT %QW613 : INT;
    F_pl1_14 AT %QW614 : INT;
    F_pl1_15 AT %QW615 : INT;
    F_pl2_00 AT %QW620 : INT;
    F_pl2_01 AT %QW621 : INT;
    F_pl2_02 AT %QW622 : INT;
    F_pl2_03 AT %QW623 : INT;
    F_pl2_04 AT %QW624 : INT;
    F_pl2_05 AT %QW625 : INT;
    F_pl2_06 AT %QW626 : INT;
    F_pl2_07 AT %QW627 : INT;
    F_pl2_08 AT %QW628 : INT;
    F_pl2_09 AT %QW629 : INT;
    F_pl2_10 AT %QW630 : INT;
    F_pl2_11 AT %QW631 : INT;
    F_pl2_12 AT %QW632 : INT;
    F_pl2_13 AT %QW633 : INT;
    F_pl2_14 AT %QW634 : INT;
    F_pl2_15 AT %QW635 : INT;
    F_pl3_00 AT %QW640 : INT;
    F_pl3_01 AT %QW641 : INT;
    F_pl3_02 AT %QW642 : INT;
    F_pl3_03 AT %QW643 : INT;
    F_pl3_04 AT %QW644 : INT;
    F_pl3_05 AT %QW645 : INT;
    F_pl3_06 AT %QW646 : INT;
    F_pl3_07 AT %QW647 : INT;
    F_pl3_08 AT %QW648 : INT;
    F_pl3_09 AT %QW649 : INT;
    F_pl3_10 AT %QW650 : INT;
    F_pl3_11 AT %QW651 : INT;
    F_pl3_12 AT %QW652 : INT;
    F_pl3_13 AT %QW653 : INT;
    F_pl3_14 AT %QW654 : INT;
    F_pl3_15 AT %QW655 : INT;
    F_pl4_00 AT %QW660 : INT;
    F_pl4_01 AT %QW661 : INT;
    F_pl4_02 AT %QW662 : INT;
    F_pl4_03 AT %QW663 : INT;
    F_pl4_04 AT %QW664 : INT;
    F_pl4_05 AT %QW665 : INT;
    F_pl4_06 AT %QW666 : INT;
    F_pl4_07 AT %QW667 : INT;
    F_pl4_08 AT %QW668 : INT;
    F_pl4_09 AT %QW669 : INT;
    F_pl4_10 AT %QW670 : INT;
    F_pl4_11 AT %QW671 : INT;
    F_pl4_12 AT %QW672 : INT;
    F_pl4_13 AT %QW673 : INT;
    F_pl4_14 AT %QW674 : INT;
    F_pl4_15 AT %QW675 : INT;
    F_pl5_00 AT %QW680 : INT;
    F_pl5_01 AT %QW681 : INT;
    F_pl5_02 AT %QW682 : INT;
    F_pl5_03 AT %QW683 : INT;
    F_pl5_04 AT %QW684 : INT;
    F_pl5_05 AT %QW685 : INT;
    F_pl5_06 AT %QW686 : INT;
    F_pl5_07 AT %QW687 : INT;
    F_pl5_08 AT %QW688 : INT;
    F_pl5_09 AT %QW689 : INT;
    F_pl5_10 AT %QW690 : INT;
    F_pl5_11 AT %QW691 : INT;
    F_pl5_12 AT %QW692 : INT;
    F_pl5_13 AT %QW693 : INT;
    F_pl5_14 AT %QW694 : INT;
    F_pl5_15 AT %QW695 : INT;
    F_mb7_00 AT %QW700 : INT;
    F_mb7_01 AT %QW701 : INT;
    F_mb7_02 AT %QW702 : INT;
    F_mb7_03 AT %QW703 : INT;
    F_mb7_04 AT %QW704 : INT;
    F_mb7_05 AT %QW705 : INT;
    F_mb7_06 AT %QW706 : INT;
    F_mb7_07 AT %QW707 : INT;
    F_mb7_08 AT %QW708 : INT;
    F_mb7_09 AT %QW709 : INT;
    F_mb7_10 AT %QW710 : INT;
    F_mb7_11 AT %QW711 : INT;
    F_mb7_12 AT %QW712 : INT;
    F_mb7_13 AT %QW713 : INT;
    F_mb7_14 AT %QW714 : INT;
    F_mb7_15 AT %QW715 : INT;
END_VAR

IF firstScan THEN
    Override     := TRUE;                 (* maintenance left it engaged *)
    Breaker_Word := 26901;
    firstScan    := FALSE;
END_IF;

(* static recon values: MB1, MB5, MB6 *)
Bay_Id := 4217;
Big_Hi := 18838;
Big_Lo := 722;
Flt_Hi := 17098;
Flt_Lo := -22938;

Heartbeat := Heartbeat + 1;
IF Heartbeat >= 30000 THEN
    Heartbeat := 0;
END_IF;

(* ---- run the challenge blocks ---- *)
beacon(Beacon_On := Beacon_On);
airlock(Inner_Closed := Inner_Closed, Suit_Ok := Suit_Ok,
        Override := Override, Cycle_Req := Cycle_Req);
holdt(Hold_Btn := Hold_Btn);
pulses(Pulse_In := Pulse_In, Count_Reset := Count_Reset);
motor(Start_PB := Start_PB, Stop_PB_NC := Stop_PB_NC);
scaler(Raw := Analog_Raw);
breakers(Word := Breaker_Word, Reset_Cmd := Breaker_Reset);
tuner(Freq := Beacon_Freq);

(* ---- re-arm outputs: put the rig back for the next team ---- *)
IF beacon.Auto_Off THEN
    Beacon_On := FALSE;
END_IF;
IF airlock.Reset_Cycle THEN
    Cycle_Req := FALSE;  Inner_Closed := FALSE;  Suit_Ok := FALSE;  Override := TRUE;
END_IF;
IF holdt.Release_Btn THEN
    Hold_Btn := FALSE;
END_IF;
IF pulses.Clear_Reset THEN
    Count_Reset := FALSE;
END_IF;
IF motor.Reset_Panel THEN
    Start_PB := FALSE;  Stop_PB_NC := FALSE;
END_IF;
IF scaler.Clear_Raw THEN
    Analog_Raw := 0;
END_IF;
IF breakers.Restore THEN
    Breaker_Word := 26901;
END_IF;
IF breakers.Clear_Reset THEN
    Breaker_Reset := FALSE;
END_IF;
IF tuner.Clear_Freq THEN
    Beacon_Freq := 0;
END_IF;

(* ---- diagnostics players can watch ---- *)
Diag_Count := pulses.Count;
Diag_Hold  := holdt.Elapsed_ds;
Diag_Eng   := scaler.Eng_x10;
Diag_Motor := 0;  IF motor.Motor_Run THEN Diag_Motor := 1; END_IF;
Diag_Door  := 0;  IF airlock.Door_Open THEN Diag_Door := 1; END_IF;
Diag_Trip  := 0;  IF breakers.Tripped THEN Diag_Trip := 1; END_IF;
Diag_Fault := 0;  IF pulses.Fault THEN Diag_Fault := 1; END_IF;
Diag_Chamber := 1013;  IF airlock.Depressurized THEN Diag_Chamber := 0; END_IF;
IG3_Locked := 0;  IF tuner.Locked THEN IG3_Locked := 1; END_IF;

(* ---- unlock bitfield ---- *)
unlock := 0;
IF beacon.Lit         THEN unlock := unlock + 1;   END_IF;   (* bit0 MB4 *)
IF airlock.Door_Open  THEN unlock := unlock + 2;   END_IF;   (* bit1 PL1 *)
IF holdt.Done         THEN unlock := unlock + 4;   END_IF;   (* bit2 PL2 *)
IF pulses.Done        THEN unlock := unlock + 8;   END_IF;   (* bit3 PL3 *)
IF motor.Done         THEN unlock := unlock + 16;  END_IF;   (* bit4 PL4 *)
IF scaler.Done        THEN unlock := unlock + 32;  END_IF;   (* bit5 PL5 *)
IF breakers.Done      THEN unlock := unlock + 64;  END_IF;   (* bit6 MB7 *)
IF tuner.Locked       THEN unlock := unlock + 128; END_IF;   (* bit7 IG3 *)
Unlock_Word := unlock;

(* ---- publish flag text (gated blocks read zero while locked) ---- *)
(* mb2: always readable *)
F_mb2_00 := 27750;
F_mb2_01 := 26465;
F_mb2_02 := 29307;
F_mb2_03 := 26419;
F_mb2_04 := 29489;
F_mb2_05 := 13172;
F_mb2_06 := 29554;
F_mb2_07 := 29535;
F_mb2_08 := 13168;
F_mb2_09 := 27444;
F_mb2_10 := 13407;
F_mb2_11 := 25459;
F_mb2_12 := 12593;
F_mb2_13 := 125;
F_mb2_14 := 0;
F_mb2_15 := 0;
(* mb3: always readable *)
F_mb3_00 := 27750;
F_mb3_01 := 26465;
F_mb3_02 := 28027;
F_mb3_03 := 25648;
F_mb3_04 := 25393;
F_mb3_05 := 28208;
F_mb3_06 := 13407;
F_mb3_07 := 25700;
F_mb3_08 := 13170;
F_mb3_09 := 29555;
F_mb3_10 := 27999;
F_mb3_11 := 29748;
F_mb3_12 := 32104;
F_mb3_13 := 0;
F_mb3_14 := 0;
F_mb3_15 := 0;
IF (unlock AND 1) <> 0 THEN   (* mb4 *)
    F_mb4_00 := 27750;
    F_mb4_01 := 26465;
    F_mb4_02 := 25211;
    F_mb4_03 := 13363;
    F_mb4_04 := 12387;
    F_mb4_05 := 24430;
    F_mb4_06 := 12652;
    F_mb4_07 := 32116;
    F_mb4_08 := 0;
    F_mb4_09 := 0;
    F_mb4_10 := 0;
    F_mb4_11 := 0;
    F_mb4_12 := 0;
    F_mb4_13 := 0;
    F_mb4_14 := 0;
    F_mb4_15 := 0;
ELSE
    F_mb4_00 := 0;
    F_mb4_01 := 0;
    F_mb4_02 := 0;
    F_mb4_03 := 0;
    F_mb4_04 := 0;
    F_mb4_05 := 0;
    F_mb4_06 := 0;
    F_mb4_07 := 0;
    F_mb4_08 := 0;
    F_mb4_09 := 0;
    F_mb4_10 := 0;
    F_mb4_11 := 0;
    F_mb4_12 := 0;
    F_mb4_13 := 0;
    F_mb4_14 := 0;
    F_mb4_15 := 0;
END_IF;
IF (unlock AND 2) <> 0 THEN   (* pl1 *)
    F_pl1_00 := 27750;
    F_pl1_01 := 26465;
    F_pl1_02 := 24955;
    F_pl1_03 := 29233;
    F_pl1_04 := 12396;
    F_pl1_05 := 27491;
    F_pl1_06 := 25439;
    F_pl1_07 := 25465;
    F_pl1_08 := 13164;
    F_pl1_09 := 32100;
    F_pl1_10 := 0;
    F_pl1_11 := 0;
    F_pl1_12 := 0;
    F_pl1_13 := 0;
    F_pl1_14 := 0;
    F_pl1_15 := 0;
ELSE
    F_pl1_00 := 0;
    F_pl1_01 := 0;
    F_pl1_02 := 0;
    F_pl1_03 := 0;
    F_pl1_04 := 0;
    F_pl1_05 := 0;
    F_pl1_06 := 0;
    F_pl1_07 := 0;
    F_pl1_08 := 0;
    F_pl1_09 := 0;
    F_pl1_10 := 0;
    F_pl1_11 := 0;
    F_pl1_12 := 0;
    F_pl1_13 := 0;
    F_pl1_14 := 0;
    F_pl1_15 := 0;
END_IF;
IF (unlock AND 4) <> 0 THEN   (* pl2 *)
    F_pl2_00 := 27750;
    F_pl2_01 := 26465;
    F_pl2_02 := 28795;
    F_pl2_03 := 29748;
    F_pl2_04 := 13105;
    F_pl2_05 := 25454;
    F_pl2_06 := 24371;
    F_pl2_07 := 29489;
    F_pl2_08 := 13407;
    F_pl2_09 := 29791;
    F_pl2_10 := 27953;
    F_pl2_11 := 29235;
    F_pl2_12 := 125;
    F_pl2_13 := 0;
    F_pl2_14 := 0;
    F_pl2_15 := 0;
ELSE
    F_pl2_00 := 0;
    F_pl2_01 := 0;
    F_pl2_02 := 0;
    F_pl2_03 := 0;
    F_pl2_04 := 0;
    F_pl2_05 := 0;
    F_pl2_06 := 0;
    F_pl2_07 := 0;
    F_pl2_08 := 0;
    F_pl2_09 := 0;
    F_pl2_10 := 0;
    F_pl2_11 := 0;
    F_pl2_12 := 0;
    F_pl2_13 := 0;
    F_pl2_14 := 0;
    F_pl2_15 := 0;
END_IF;
IF (unlock AND 8) <> 0 THEN   (* pl3 *)
    F_pl3_00 := 27750;
    F_pl3_01 := 26465;
    F_pl3_02 := 13179;
    F_pl3_03 := 26468;
    F_pl3_04 := 29491;
    F_pl3_05 := 28255;
    F_pl3_06 := 29744;
    F_pl3_07 := 27743;
    F_pl3_08 := 30259;
    F_pl3_09 := 27699;
    F_pl3_10 := 32115;
    F_pl3_11 := 0;
    F_pl3_12 := 0;
    F_pl3_13 := 0;
    F_pl3_14 := 0;
    F_pl3_15 := 0;
ELSE
    F_pl3_00 := 0;
    F_pl3_01 := 0;
    F_pl3_02 := 0;
    F_pl3_03 := 0;
    F_pl3_04 := 0;
    F_pl3_05 := 0;
    F_pl3_06 := 0;
    F_pl3_07 := 0;
    F_pl3_08 := 0;
    F_pl3_09 := 0;
    F_pl3_10 := 0;
    F_pl3_11 := 0;
    F_pl3_12 := 0;
    F_pl3_13 := 0;
    F_pl3_14 := 0;
    F_pl3_15 := 0;
END_IF;
IF (unlock AND 16) <> 0 THEN   (* pl4 *)
    F_pl4_00 := 27750;
    F_pl4_01 := 26465;
    F_pl4_02 := 29563;
    F_pl4_03 := 13363;
    F_pl4_04 := 24428;
    F_pl4_05 := 28209;
    F_pl4_06 := 27743;
    F_pl4_07 := 29748;
    F_pl4_08 := 26723;
    F_pl4_09 := 25651;
    F_pl4_10 := 125;
    F_pl4_11 := 0;
    F_pl4_12 := 0;
    F_pl4_13 := 0;
    F_pl4_14 := 0;
    F_pl4_15 := 0;
ELSE
    F_pl4_00 := 0;
    F_pl4_01 := 0;
    F_pl4_02 := 0;
    F_pl4_03 := 0;
    F_pl4_04 := 0;
    F_pl4_05 := 0;
    F_pl4_06 := 0;
    F_pl4_07 := 0;
    F_pl4_08 := 0;
    F_pl4_09 := 0;
    F_pl4_10 := 0;
    F_pl4_11 := 0;
    F_pl4_12 := 0;
    F_pl4_13 := 0;
    F_pl4_14 := 0;
    F_pl4_15 := 0;
END_IF;
IF (unlock AND 32) <> 0 THEN   (* pl5 *)
    F_pl5_00 := 27750;
    F_pl5_01 := 26465;
    F_pl5_02 := 26235;
    F_pl5_03 := 30000;
    F_pl5_04 := 24434;
    F_pl5_05 := 12404;
    F_pl5_06 := 29791;
    F_pl5_07 := 13175;
    F_pl5_08 := 29806;
    F_pl5_09 := 24441;
    F_pl5_10 := 12653;
    F_pl5_11 := 27756;
    F_pl5_12 := 13361;
    F_pl5_13 := 28781;
    F_pl5_14 := 32115;
    F_pl5_15 := 0;
ELSE
    F_pl5_00 := 0;
    F_pl5_01 := 0;
    F_pl5_02 := 0;
    F_pl5_03 := 0;
    F_pl5_04 := 0;
    F_pl5_05 := 0;
    F_pl5_06 := 0;
    F_pl5_07 := 0;
    F_pl5_08 := 0;
    F_pl5_09 := 0;
    F_pl5_10 := 0;
    F_pl5_11 := 0;
    F_pl5_12 := 0;
    F_pl5_13 := 0;
    F_pl5_14 := 0;
    F_pl5_15 := 0;
END_IF;
IF (unlock AND 64) <> 0 THEN   (* mb7 *)
    F_mb7_00 := 27750;
    F_mb7_01 := 26465;
    F_mb7_02 := 28027;
    F_mb7_03 := 29492;
    F_mb7_04 := 24427;
    F_mb7_05 := 13154;
    F_mb7_06 := 12390;
    F_mb7_07 := 13170;
    F_mb7_08 := 31071;
    F_mb7_09 := 30000;
    F_mb7_10 := 30559;
    F_mb7_11 := 12658;
    F_mb7_12 := 13172;
    F_mb7_13 := 125;
    F_mb7_14 := 0;
    F_mb7_15 := 0;
ELSE
    F_mb7_00 := 0;
    F_mb7_01 := 0;
    F_mb7_02 := 0;
    F_mb7_03 := 0;
    F_mb7_04 := 0;
    F_mb7_05 := 0;
    F_mb7_06 := 0;
    F_mb7_07 := 0;
    F_mb7_08 := 0;
    F_mb7_09 := 0;
    F_mb7_10 := 0;
    F_mb7_11 := 0;
    F_mb7_12 := 0;
    F_mb7_13 := 0;
    F_mb7_14 := 0;
    F_mb7_15 := 0;
END_IF;
END_PROGRAM

CONFIGURATION Config0
    RESOURCE Res0 ON PLC
        TASK Main(INTERVAL := T#100ms, PRIORITY := 0);
        PROGRAM Inst0 WITH Main : prog0;
    END_RESOURCE
END_CONFIGURATION

