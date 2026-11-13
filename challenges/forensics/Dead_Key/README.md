# Dead Key

**Category:** Forensics
**Difficulty:** Medium
**Author:** Voyager 1

## Description

The recovery drone that reached the derelict RazorPowerCo relay station
couldn't save the operator, but it pulled one intact file: a partial capture
of the station's local network segment from the final half hour before
contact was lost.

Every crew member wears a biomonitor that reports to the station's
telemetry broker. Somewhere in that traffic, one of them goes from routine to
catastrophic. Find the exact moment it happened.

Submit the flag as `flag{...}`, with the contents being the UTC date and time
the critical failure alert was sent, as `YYYY-MM-DD_HH-MM-SS` (year-month-day, then hour-minute-second, 24-hour clock) between the braces,
rounded down to the whole second. The capture runs on the station's own
calendar, so its dates will look far in the future.

## Files Provided

- `console_capture.pcap` - partial capture of the relay station's local
  network segment, covering roughly the final half hour before contact was
  lost.
