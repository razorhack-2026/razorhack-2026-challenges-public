# Pulsar Dropbox

**Category:** Forensics  
**Difficulty:** Medium  
**Author:** Jebediah Kerman  

## Description

The file share went down again, so Dr. Vance's colleague did what any reasonable person does
under deadline: mailed the observation over in pieces. Then someone locked the last attachment
"for safety" and went on leave.

We pulled her inbox off the station relay before it was wiped. Whatever she was sent is still in
there somewhere, scattered between the payroll reminders and the calibration logs. Put it back
together, look at what it shows you, and that will tell you how to open the rest.

The relay's clock was drifting during the dump, so the message timestamps came out unreliable —
don't trust the dates to tell you what order anything arrived in.

## Files Provided

- `inbox.mbox`

## Notes

- `inbox.mbox` is a standard Unix mbox. Any mail client that can import one will do — in
  Thunderbird, drop it into your profile's `Mail/Local Folders/` named `inbox` with no
  extension, then switch to Threaded view. Parsing it with a script works just as well.
- Treat attachments as **raw bytes**. Opening one in a text editor and re-saving it can alter
  the file on disk.
