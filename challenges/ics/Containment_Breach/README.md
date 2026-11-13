# Containment Breach

**Category:** ICS
**Difficulty:** Medium
**Author:** Voyager 1

## Description

The KEEPER OF TOMORROW's cargo hold carries a terraforming culture bound for Novare, *Ignis vorax*, a thermophilic
microorganism that feeds on heat energy. Three culture vessels share one cryo-suppression plant that keeps the
colony dormant; a read-only HMI shows all three vessels nominal. Its address is the `HMI` line in this
challenge's connection info.

You have network access to three Modbus/TCP controllers and one plant
telemetry endpoint, all at the `Modbus` address in the connection info. The register map is provided.

Vessel C is under local control — its own setpoints won't take a remote write. Defeat the containment interlock
anyway and drive Vessel C's colony past its breach threshold. The flag will appear automatically when it
ruptures.

## Files Provided

- `dist/REGISTER_MAP.md` - the controller's Modbus register map
