(* Unit tests for ECLSS_Core run with: strucpp ECLSS_Core.st --test test_eclss.st
   Verifies the plant drifts out of spec while the puzzle routine is armed,
   that the correct disarm code stops it, that wrong codes lock out, and
   that correcting the setpoints brings every channel back into range.
   SETUP runs before each TEST, so each test gets a fresh ECLSS_Core. *)
SETUP
VAR
    e : ECLSS_Core;
END_VAR
END_SETUP

TEST 'starts armed with the cabin already out of spec'
    e(dt := 0.1, O2_SP_x100 := 2095, O2_Kp_x10 := 20, CDRA_Mode := 1,
      CDRA_HalfCycle_s := 30, Temp_SP_x100 := 2250, TCS_Kp_x10 := 30,
      Disarm_Code := 0, OGA_Inhibit := FALSE, CDRA_Heater_En := FALSE,
      TCS_Reverse := FALSE, Heater_Override := FALSE);
    ASSERT_TRUE(e.MaintSyncArmed);
    ASSERT_TRUE(e.O2_x100 < 1950);
    ASSERT_TRUE(e.CO2_ppm > 5000);
    ASSERT_TRUE(e.Temp_x100 > 2700);
    ASSERT_EQ(e.FlagsEarned, 0);
END_TEST

TEST 'an untouched ship earns no objective in 10 minutes'
VAR
    k : INT;
    seen : INT := 0;
    sp : INT := 2095; kp : INT := 20; md : INT := 1; hc : INT := 30;
    ts : INT := 2250; tk : INT := 30; dc : INT := 0;
    b0 : BOOL; b1 : BOOL; b2 : BOOL; b3 : BOOL;
END_VAR
    (* regression: the cabin used to start in range, so bits 0-2 set on the
       first scan and flags 3-5 were published before anyone touched it *)
    FOR k := 1 TO 6000 DO
        e(dt := 0.1, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
          CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
          Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
          TCS_Reverse := b2, Heater_Override := b3);
        sp := e.O2_SP_x100; md := e.CDRA_Mode; ts := e.Temp_SP_x100; dc := e.Disarm_Code;
        seen := seen OR e.FlagsEarned;
    END_FOR;
    ASSERT_EQ(seen, 0);
END_TEST

TEST 'fixing O2 and temperature earns bits 0 and 2 inside one 20 s window'
VAR
    k : INT;
    seen : INT := 0;
    sp : INT := 2095; kp : INT := 20; md : INT := 1; hc : INT := 30;
    ts : INT := 2250; tk : INT := 30; dc : INT := 0;
    b0 : BOOL; b1 : BOOL; b2 : BOOL; b3 : BOOL;
END_VAR
    (* first scan: MaintSync forces the mis-config *)
    e(dt := 0.1, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
      CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
      Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
      TCS_Reverse := b2, Heater_Override := b3);
    (* the crew writes the nominal setpoints once, without disarming *)
    sp := 2095; ts := 2250; md := e.CDRA_Mode; dc := e.Disarm_Code;
    FOR k := 1 TO 150 DO
        e(dt := 0.1, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
          CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
          Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
          TCS_Reverse := b2, Heater_Override := b3);
        sp := e.O2_SP_x100; md := e.CDRA_Mode; ts := e.Temp_SP_x100; dc := e.Disarm_Code;
        seen := seen OR e.FlagsEarned;
    END_FOR;
    ASSERT_EQ(seen AND 5, 5);
    ASSERT_TRUE(e.MaintSyncArmed);
END_TEST

TEST 'one scrubber fix does not bring CO2 under 5000 while armed'
VAR
    k : INT;
    seen : INT := 0;
    sp : INT := 2095; kp : INT := 20; md : INT := 1; hc : INT := 30;
    ts : INT := 2250; tk : INT := 30; dc : INT := 0;
    b0 : BOOL; b1 : BOOL; b2 : BOOL; b3 : BOOL;
END_VAR
    e(dt := 0.1, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
      CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
      Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
      TCS_Reverse := b2, Heater_Override := b3);
    (* AUTO and the regen heater, written once; MaintSync re-pins the bed *)
    md := 1; b1 := TRUE; dc := e.Disarm_Code;
    FOR k := 1 TO 6000 DO
        e(dt := 0.1, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
          CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
          Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
          TCS_Reverse := b2, Heater_Override := b3);
        sp := e.O2_SP_x100; md := e.CDRA_Mode; ts := e.Temp_SP_x100; dc := e.Disarm_Code;
        seen := seen OR e.FlagsEarned;
    END_FOR;
    ASSERT_EQ(seen AND 2, 0);
END_TEST

TEST 'keeping the scrubber in AUTO brings CO2 under 5000 without disarming'
VAR
    k : INT;
    seen : INT := 0;
    sp : INT := 2095; kp : INT := 20; md : INT := 1; hc : INT := 30;
    ts : INT := 2250; tk : INT := 30; dc : INT := 0;
    b0 : BOOL; b1 : BOOL := TRUE; b2 : BOOL; b3 : BOOL;
END_VAR
    (* the crew puts AUTO back every time MaintSync re-pins the bed *)
    FOR k := 1 TO 3000 DO
        e(dt := 0.1, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
          CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
          Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
          TCS_Reverse := b2, Heater_Override := b3);
        sp := e.O2_SP_x100; ts := e.Temp_SP_x100; dc := e.Disarm_Code;
        md := e.CDRA_Mode;
        IF md = 2 THEN md := 1; END_IF;
        seen := seen OR e.FlagsEarned;
    END_FOR;
    ASSERT_EQ(seen AND 2, 2);
    ASSERT_TRUE(e.MaintSyncArmed);
END_TEST

TEST 'armed routine forces the mis-config on first scan'
    e(dt := 0.1, O2_SP_x100 := 2095, O2_Kp_x10 := 20, CDRA_Mode := 1,
      CDRA_HalfCycle_s := 30, Temp_SP_x100 := 2250, TCS_Kp_x10 := 30,
      Disarm_Code := 0, OGA_Inhibit := FALSE, CDRA_Heater_En := FALSE,
      TCS_Reverse := FALSE, Heater_Override := FALSE);
    ASSERT_EQ(e.O2_SP_x100, 1850);
    ASSERT_EQ(e.CDRA_Mode, 2);
    ASSERT_EQ(e.Temp_SP_x100, 3100);
END_TEST

TEST 'armed mis-config drives O2 below the 19.5 floor within 60 s'
VAR
    k : INT;
    sp : INT := 2095; kp : INT := 20; md : INT := 1; hc : INT := 30;
    ts : INT := 2250; tk : INT := 30; dc : INT := 0;
    b0 : BOOL; b1 : BOOL; b2 : BOOL; b3 : BOOL;
END_VAR
    FOR k := 1 TO 600 DO
        e(dt := 0.1, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
          CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
          Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
          TCS_Reverse := b2, Heater_Override := b3);
        (* mirror prog0: copy FB-modified setpoints back to the registers *)
        sp := e.O2_SP_x100; md := e.CDRA_Mode; ts := e.Temp_SP_x100; dc := e.Disarm_Code;
    END_FOR;
    ASSERT_TRUE(e.O2_x100 < 1950);
    ASSERT_EQ(e.FlagsEarned MOD 2, 0);
END_TEST

TEST 'armed mis-config drives CO2 over 5000 ppm within 3 min'
VAR
    k : INT;
    sp : INT := 2095; kp : INT := 20; md : INT := 1; hc : INT := 30;
    ts : INT := 2250; tk : INT := 30; dc : INT := 0;
    b0 : BOOL; b1 : BOOL; b2 : BOOL; b3 : BOOL;
END_VAR
    FOR k := 1 TO 1800 DO
        e(dt := 0.1, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
          CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
          Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
          TCS_Reverse := b2, Heater_Override := b3);
        (* mirror prog0: copy FB-modified setpoints back to the registers *)
        sp := e.O2_SP_x100; md := e.CDRA_Mode; ts := e.Temp_SP_x100; dc := e.Disarm_Code;
    END_FOR;
    ASSERT_TRUE(e.CO2_ppm > 5000);
END_TEST

TEST 'armed mis-config drives the cabin above 27 C within 30 s'
VAR
    k : INT;
    sp : INT := 2095; kp : INT := 20; md : INT := 1; hc : INT := 30;
    ts : INT := 2250; tk : INT := 30; dc : INT := 0;
    b0 : BOOL; b1 : BOOL; b2 : BOOL; b3 : BOOL;
END_VAR
    FOR k := 1 TO 300 DO
        e(dt := 0.1, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
          CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
          Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
          TCS_Reverse := b2, Heater_Override := b3);
        (* mirror prog0: copy FB-modified setpoints back to the registers *)
        sp := e.O2_SP_x100; md := e.CDRA_Mode; ts := e.Temp_SP_x100; dc := e.Disarm_Code;
    END_FOR;
    ASSERT_TRUE(e.Temp_x100 > 2700);
END_TEST

TEST 'wrong disarm code does not disarm'
    e(dt := 0.1, O2_SP_x100 := 2095, O2_Kp_x10 := 20, CDRA_Mode := 1,
      CDRA_HalfCycle_s := 30, Temp_SP_x100 := 2250, TCS_Kp_x10 := 30,
      Disarm_Code := 1111, OGA_Inhibit := FALSE, CDRA_Heater_En := FALSE,
      TCS_Reverse := FALSE, Heater_Override := FALSE);
    ASSERT_TRUE(e.MaintSyncArmed);
END_TEST

TEST 'five wrong codes trigger tamper lockout'
VAR
    k : INT;
END_VAR
    FOR k := 1 TO 5 DO
        e(dt := 0.1, O2_SP_x100 := 2095, O2_Kp_x10 := 20, CDRA_Mode := 1,
          CDRA_HalfCycle_s := 30, Temp_SP_x100 := 2250, TCS_Kp_x10 := 30,
          Disarm_Code := 1000 + k, OGA_Inhibit := FALSE, CDRA_Heater_En := FALSE,
          TCS_Reverse := FALSE, Heater_Override := FALSE);
    END_FOR;
    ASSERT_TRUE(e.TamperLockout);
END_TEST

TEST 'correct code disarms the routine'
    e(dt := 0.1, O2_SP_x100 := 2095, O2_Kp_x10 := 20, CDRA_Mode := 1,
      CDRA_HalfCycle_s := 30, Temp_SP_x100 := 2250, TCS_Kp_x10 := 30,
      Disarm_Code := 7982, OGA_Inhibit := FALSE, CDRA_Heater_En := FALSE,
      TCS_Reverse := FALSE, Heater_Override := FALSE);
    ASSERT_FALSE(e.MaintSyncArmed);
END_TEST

TEST 'from a fully sabotaged ship, disarm + correct setpoints reach the final hold'
VAR
    k : INT;
    sp : INT := 2095; kp : INT := 20; md : INT := 1; hc : INT := 30;
    ts : INT := 2250; tk : INT := 30; dc : INT := 0;
    b0 : BOOL; b1 : BOOL; b2 : BOOL; b3 : BOOL;
END_VAR
    (* 1) leave the ship armed for 4 minutes so every channel is out of spec *)
    FOR k := 1 TO 2400 DO
        e(dt := 0.1, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
          CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
          Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
          TCS_Reverse := b2, Heater_Override := b3);
        sp := e.O2_SP_x100; md := e.CDRA_Mode; ts := e.Temp_SP_x100; dc := e.Disarm_Code;
    END_FOR;
    ASSERT_TRUE(e.O2_x100 < 1950);
    ASSERT_TRUE(e.CO2_ppm > 5000);
    ASSERT_TRUE(e.Temp_x100 > 2700);

    (* 2) the documented fix: disarm, then the nominal setpoints + regen heater *)
    dc := 7982;
    sp := 2095; md := 1; ts := 2250; b1 := TRUE;
    FOR k := 1 TO 3000 DO
        e(dt := 0.1, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
          CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
          Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
          TCS_Reverse := b2, Heater_Override := b3);
        sp := e.O2_SP_x100; md := e.CDRA_Mode; ts := e.Temp_SP_x100; dc := e.Disarm_Code;
    END_FOR;
    ASSERT_FALSE(e.MaintSyncArmed);
    ASSERT_TRUE(e.O2_x100 >= 2050);
    ASSERT_TRUE(e.O2_x100 <= 2150);
    ASSERT_TRUE(e.CO2_ppm <= 5000);
    ASSERT_TRUE(e.Temp_x100 >= 1800);
    ASSERT_TRUE(e.Temp_x100 <= 2700);
    ASSERT_EQ(e.AlarmWord, 0);
    ASSERT_EQ(e.FlagsEarned, 31);
END_TEST

TEST 'no coils needed: disarm and the three setpoints reach the final hold'
VAR
    k : INT;
    sp : INT := 2095; kp : INT := 20; md : INT := 1; hc : INT := 30;
    ts : INT := 2250; tk : INT := 30; dc : INT := 0;
    b0 : BOOL; b1 : BOOL; b2 : BOOL; b3 : BOOL;
END_VAR
    (* players can only identify holding registers from the HMI and /maint,
       never the coils, so the whole ship must be solvable with every coil
       left OFF - even after an hour of sabotage (CO2 at its cap) *)
    FOR k := 1 TO 7200 DO
        e(dt := 0.5, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
          CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
          Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
          TCS_Reverse := b2, Heater_Override := b3);
        sp := e.O2_SP_x100; md := e.CDRA_Mode; ts := e.Temp_SP_x100; dc := e.Disarm_Code;
    END_FOR;
    dc := 7982;
    sp := 2095; md := 1; ts := 2250;
    FOR k := 1 TO 3000 DO
        e(dt := 0.1, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
          CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
          Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
          TCS_Reverse := b2, Heater_Override := b3);
        sp := e.O2_SP_x100; md := e.CDRA_Mode; ts := e.Temp_SP_x100; dc := e.Disarm_Code;
    END_FOR;
    ASSERT_FALSE(b0 OR b1 OR b2 OR b3);
    ASSERT_EQ(e.AlarmWord, 0);
    ASSERT_EQ(e.FlagsEarned, 31);
END_TEST

TEST 'a ship left armed for an hour keeps CO2 bounded and still recovers in 5 min'
VAR
    k : INT;
    sp : INT := 2095; kp : INT := 20; md : INT := 1; hc : INT := 30;
    ts : INT := 2250; tk : INT := 30; dc : INT := 0;
    b0 : BOOL; b1 : BOOL; b2 : BOOL; b3 : BOOL;
END_VAR
    (* regression: CO2 used to climb without limit and wrap the INT register
       negative (61,136 ppm read as -4,400) after ~18 min unattended *)
    FOR k := 1 TO 7200 DO
        e(dt := 0.5, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
          CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
          Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
          TCS_Reverse := b2, Heater_Override := b3);
        sp := e.O2_SP_x100; md := e.CDRA_Mode; ts := e.Temp_SP_x100; dc := e.Disarm_Code;
    END_FOR;
    ASSERT_TRUE(e.CO2_ppm > 5000);
    ASSERT_TRUE(e.CO2_ppm <= 12000);
    ASSERT_TRUE(e.Temp_x100 > 0);
    ASSERT_TRUE(e.O2_x100 > 0);

    dc := 7982;
    sp := 2095; md := 1; ts := 2250; b1 := TRUE;
    FOR k := 1 TO 3000 DO
        e(dt := 0.1, O2_SP_x100 := sp, O2_Kp_x10 := kp, CDRA_Mode := md,
          CDRA_HalfCycle_s := hc, Temp_SP_x100 := ts, TCS_Kp_x10 := tk,
          Disarm_Code := dc, OGA_Inhibit := b0, CDRA_Heater_En := b1,
          TCS_Reverse := b2, Heater_Override := b3);
        sp := e.O2_SP_x100; md := e.CDRA_Mode; ts := e.Temp_SP_x100; dc := e.Disarm_Code;
    END_FOR;
    ASSERT_EQ(e.AlarmWord, 0);
    ASSERT_EQ(e.FlagsEarned, 31);
END_TEST
