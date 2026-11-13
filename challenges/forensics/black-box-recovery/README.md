# Black Box Recovery

**Category:** Forensics  
**Difficulty:** Hard  
**Author:** Jebediah Kerman  

## Description

The probe came down hard. Salvage pulled its flight recorder out of the wreckage and imaged
the storage before anything else could go wrong.

In its last seconds the flight computer logged the abort sequence and the self-destruct
override code it accepted. Then the log was deleted, and the crash finished the job on the
drive's file table. Every recovery tool we own finds the file, reports its size, and hands
back nothing.

The recorder is stubborn, though. It kept what it could. Get us that override code.

## Files Provided

- `blackbox.img.xz` — xz-compressed raw NTFS image (96 MB unpacked)

## Notes

- Work on a copy of the image. Nothing here requires you to modify it.
