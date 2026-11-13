(* Unit tests for the Training Bay function blocks.
   Rendered by build_training.py (secrets filled in) to
   build/training/test_training.st, then:
     strucpp build/training/TRAIN_FBs.st --test build/training/test_training.st
   ADVANCE_TIME(ns) moves the scan clock. A TON samples the clock when it is
   called, so "call, advance the full duration, call again" is exactly what
   the PLC sees over that many scans. 1 s = 1000000000 ns. *)

TEST 'MB4 beacon: lit while on, auto-off after 15 s'
VAR
    b : FB_Beacon;
END_VAR
    b(Beacon_On := TRUE);
    ASSERT_TRUE(b.Lit);
    ASSERT_FALSE(b.Auto_Off);
    ADVANCE_TIME(14000000000);
    b(Beacon_On := TRUE);
    ASSERT_FALSE(b.Auto_Off);
    ADVANCE_TIME(1000000000);
    b(Beacon_On := TRUE);
    ASSERT_TRUE(b.Auto_Off);
END_TEST

TEST 'PL1 airlock: override blocks the door even when pumped down'
VAR
    a : FB_Airlock;
END_VAR
    a(Inner_Closed := TRUE, Suit_Ok := TRUE, Override := TRUE, Cycle_Req := TRUE);
    ADVANCE_TIME(6000000000);
    a(Inner_Closed := TRUE, Suit_Ok := TRUE, Override := TRUE, Cycle_Req := TRUE);
    ASSERT_TRUE(a.Depressurized);
    ASSERT_FALSE(a.Door_Open);
END_TEST

TEST 'PL1 airlock: door waits for the 4 s pump-down'
VAR
    a : FB_Airlock;
END_VAR
    a(Inner_Closed := TRUE, Suit_Ok := TRUE, Override := FALSE, Cycle_Req := TRUE);
    ADVANCE_TIME(3000000000);
    a(Inner_Closed := TRUE, Suit_Ok := TRUE, Override := FALSE, Cycle_Req := TRUE);
    ASSERT_FALSE(a.Door_Open);
    ADVANCE_TIME(1000000000);
    a(Inner_Closed := TRUE, Suit_Ok := TRUE, Override := FALSE, Cycle_Req := TRUE);
    ASSERT_TRUE(a.Door_Open);
END_TEST

TEST 'PL1 airlock: opening the inner door re-pressurizes'
VAR
    a : FB_Airlock;
END_VAR
    a(Inner_Closed := TRUE, Suit_Ok := TRUE, Override := FALSE, Cycle_Req := TRUE);
    ADVANCE_TIME(5000000000);
    a(Inner_Closed := TRUE, Suit_Ok := TRUE, Override := FALSE, Cycle_Req := TRUE);
    ASSERT_TRUE(a.Door_Open);
    a(Inner_Closed := FALSE, Suit_Ok := TRUE, Override := FALSE, Cycle_Req := TRUE);
    ASSERT_FALSE(a.Depressurized);
    ASSERT_FALSE(a.Door_Open);
END_TEST

TEST 'PL1 airlock: re-arms 20 s after opening'
VAR
    a : FB_Airlock;
END_VAR
    a(Inner_Closed := TRUE, Suit_Ok := TRUE, Override := FALSE, Cycle_Req := TRUE);
    ADVANCE_TIME(4000000000);
    a(Inner_Closed := TRUE, Suit_Ok := TRUE, Override := FALSE, Cycle_Req := TRUE);
    ASSERT_TRUE(a.Door_Open);
    ASSERT_FALSE(a.Reset_Cycle);
    ADVANCE_TIME(20000000000);
    a(Inner_Closed := TRUE, Suit_Ok := TRUE, Override := FALSE, Cycle_Req := TRUE);
    ASSERT_TRUE(a.Reset_Cycle);
END_TEST

TEST 'PL2 hold: letting go at 4 s restarts the timer'
VAR
    h : FB_HoldTimer;
END_VAR
    h(Hold_Btn := TRUE);
    ADVANCE_TIME(4000000000);
    h(Hold_Btn := TRUE);
    ASSERT_FALSE(h.Done);
    ASSERT_EQ(h.Elapsed_ds, 40);
    h(Hold_Btn := FALSE);
    ASSERT_EQ(h.Elapsed_ds, 0);
    h(Hold_Btn := TRUE);
    ADVANCE_TIME(2000000000);
    h(Hold_Btn := TRUE);
    ASSERT_FALSE(h.Done);
END_TEST

TEST 'PL2 hold: 5 s continuous unlocks, window closes after 20 s'
VAR
    h : FB_HoldTimer;
END_VAR
    h(Hold_Btn := TRUE);
    ADVANCE_TIME(5000000000);
    h(Hold_Btn := TRUE);
    ASSERT_TRUE(h.Done);
    ASSERT_TRUE(h.Release_Btn);
    h(Hold_Btn := FALSE);
    ASSERT_TRUE(h.Done);
    ADVANCE_TIME(20000000000);
    h(Hold_Btn := FALSE);
    ASSERT_FALSE(h.Done);
END_TEST

TEST 'PL3 counter: holding the input ON counts only once'
VAR
    p : FB_PulseCounter;
    k : INT;
END_VAR
    FOR k := 1 TO 30 DO
        p(Pulse_In := TRUE, Count_Reset := FALSE);
    END_FOR;
    ASSERT_EQ(p.Count, 1);
END_TEST

TEST 'PL3 counter: exactly 7 edges then 2 s off unlocks'
VAR
    p : FB_PulseCounter;
    k : INT;
END_VAR
    FOR k := 1 TO 7 DO
        p(Pulse_In := TRUE, Count_Reset := FALSE);
        p(Pulse_In := FALSE, Count_Reset := FALSE);
    END_FOR;
    ASSERT_EQ(p.Count, 7);
    ASSERT_FALSE(p.Done);
    ADVANCE_TIME(2000000000);
    p(Pulse_In := FALSE, Count_Reset := FALSE);
    ASSERT_TRUE(p.Done);
END_TEST

TEST 'PL3 counter: an 8th pulse faults, and only reset clears it'
VAR
    p : FB_PulseCounter;
    k : INT;
END_VAR
    FOR k := 1 TO 8 DO
        p(Pulse_In := TRUE, Count_Reset := FALSE);
        p(Pulse_In := FALSE, Count_Reset := FALSE);
    END_FOR;
    ASSERT_TRUE(p.Fault);
    ADVANCE_TIME(3000000000);
    p(Pulse_In := FALSE, Count_Reset := FALSE);
    ASSERT_FALSE(p.Done);
    p(Pulse_In := FALSE, Count_Reset := TRUE);
    ASSERT_EQ(p.Count, 0);
    ASSERT_FALSE(p.Fault);
    ASSERT_TRUE(p.Clear_Reset);
END_TEST

TEST 'PL4 motor: STOP input FALSE (pressed/NC open) blocks start'
VAR
    m : FB_MotorSealIn;
END_VAR
    m(Start_PB := TRUE, Stop_PB_NC := FALSE);
    ASSERT_FALSE(m.Motor_Run);
END_TEST

TEST 'PL4 motor: seal-in holds after START released, unlocks at 3 s'
VAR
    m : FB_MotorSealIn;
END_VAR
    m(Start_PB := TRUE, Stop_PB_NC := TRUE);
    ASSERT_TRUE(m.Motor_Run);
    m(Start_PB := FALSE, Stop_PB_NC := TRUE);
    ASSERT_TRUE(m.Motor_Run);
    ASSERT_FALSE(m.Done);
    ADVANCE_TIME(3000000000);
    m(Start_PB := FALSE, Stop_PB_NC := TRUE);
    ASSERT_TRUE(m.Done);
END_TEST

TEST 'PL4 motor: holding START does not count as sealed-in'
VAR
    m : FB_MotorSealIn;
END_VAR
    m(Start_PB := TRUE, Stop_PB_NC := TRUE);
    ADVANCE_TIME(5000000000);
    m(Start_PB := TRUE, Stop_PB_NC := TRUE);
    ASSERT_TRUE(m.Motor_Run);
    ASSERT_FALSE(m.Done);
END_TEST

TEST 'PL4 motor: pressing STOP drops the seal-in'
VAR
    m : FB_MotorSealIn;
END_VAR
    m(Start_PB := TRUE, Stop_PB_NC := TRUE);
    m(Start_PB := FALSE, Stop_PB_NC := TRUE);
    ASSERT_TRUE(m.Motor_Run);
    m(Start_PB := FALSE, Stop_PB_NC := FALSE);
    ASSERT_FALSE(m.Motor_Run);
    m(Start_PB := FALSE, Stop_PB_NC := TRUE);
    ASSERT_FALSE(m.Motor_Run);
END_TEST

TEST 'PL5 scaling: 4 mA, 20 mA and wire break'
VAR
    s : FB_Scaling;
END_VAR
    s(Raw := 6554);
    ASSERT_EQ(s.Eng_x10, 0);
    s(Raw := 32767);
    ASSERT_EQ(s.Eng_x10, 1000);
    s(Raw := 0);
    ASSERT_TRUE(s.Wire_Break);
    ASSERT_EQ(s.Eng_x10, -1);
END_TEST

TEST 'PL5 scaling: 62.5 % held 2 s unlocks'
VAR
    s : FB_Scaling;
END_VAR
    s(Raw := 22937);
    ASSERT_EQ(s.Eng_x10, 625);
    ASSERT_FALSE(s.Done);
    ADVANCE_TIME(2000000000);
    s(Raw := 22937);
    ASSERT_TRUE(s.Done);
END_TEST

TEST 'PL5 scaling: 62.5 % of the raw range (not of the mA span) is wrong'
VAR
    s : FB_Scaling;
END_VAR
    s(Raw := 20479);
    ADVANCE_TIME(3000000000);
    s(Raw := 20479);
    ASSERT_FALSE(s.Done);
END_TEST

TEST 'MB7 breakers: setting only the target bit unlocks'
VAR
    br : FB_BreakerPanel;
END_VAR
    br(Word := 26901, Reset_Cmd := FALSE);
    ASSERT_FALSE(br.Tripped);
    br(Word := 27413, Reset_Cmd := FALSE);
    ASSERT_TRUE(br.Done);
    ASSERT_FALSE(br.Tripped);
END_TEST

TEST 'MB7 breakers: blind write of just the bit trips; reset recovers'
VAR
    br : FB_BreakerPanel;
END_VAR
    br(Word := 26901, Reset_Cmd := FALSE);
    br(Word := 512, Reset_Cmd := FALSE);
    ASSERT_TRUE(br.Tripped);
    ASSERT_FALSE(br.Done);
    br(Word := 27413, Reset_Cmd := FALSE);
    ASSERT_FALSE(br.Done);
    br(Word := 27413, Reset_Cmd := TRUE);
    ASSERT_FALSE(br.Tripped);
    ASSERT_TRUE(br.Restore);
    br(Word := 26901, Reset_Cmd := FALSE);
    br(Word := 27413, Reset_Cmd := FALSE);
    ASSERT_TRUE(br.Done);
END_TEST

TEST 'IG3 tuner: locks on target, clears after 30 s'
VAR
    t : FB_Tuner;
END_VAR
    t(Freq := 1000);
    ASSERT_FALSE(t.Locked);
    t(Freq := 1420);
    ASSERT_TRUE(t.Locked);
    ASSERT_FALSE(t.Clear_Freq);
    ADVANCE_TIME(30000000000);
    t(Freq := 1420);
    ASSERT_TRUE(t.Clear_Freq);
END_TEST
