# Ghost Command

**Category:** ICS
**Difficulty:** Medium
**Author:** Voyager 1

## Description

RazerPowerCo's substation feed to Docking Ring 3 runs IEC 61850 GOOSE
between two IEDs, `IED-PROT-03` and `IED-BKR-07`. Maintenance ran a
breaker-exercise routine on the segment during a scheduled
test window. The whole thing got captured in `substation_test_window.pcap`.

During that window the breaker actually tripped once, for real. Nobody
flagged it at the time.

A jump box sits on the same segment the capture came from, `10.13.39.0/24`:

```
ssh player@<challenge-host> -p 2223
password: gh0stcmd
```

Passwordless sudo. `tcpdump`, `tshark`, and Python with `scapy` are
already installed.

IED-BKR-07 reports status over Modbus/TCP on `10.13.39.20:502`. Flag's
in its holding registers once the breaker trips again.

## Files Provided

- `dist/substation_test_window.pcap` - packet capture of the maintenance
  test window
