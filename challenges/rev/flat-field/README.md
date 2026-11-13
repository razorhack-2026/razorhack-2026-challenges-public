# Flat Field

**Category:** Reverse Engineering
**Difficulty:** Hard

Before downlink, the probe's imaging pipeline runs every frame through `lenscal`, a
lens-calibration utility that applies a calibration mask to the frame.

Ground received a calibrated frame of NGC 6872, the Condor Galaxy. The calibration mask
that went with it was lost in transit, and mission control needs it back. All you have is
the calibrated frame and the tool that produced it.

## Files

- `condor_cal.png`: the calibrated frame as received by ground
- `lenscal`: the probe's calibration utility

Image credit: NASA/JPL-Caltech (PIA16613), modified.
