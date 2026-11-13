# Flat Field — build notes

Built on Windows 2026-10-05 with Python 3.12 (Pillow, numpy) and zig 0.17.0 (`zig cc`).
`stb_image.h` / `stb_image_write.h` are vendored from github.com/nothings/stb (public domain / MIT).

```sh
# 1. frame: crop + 1080p rescale + seeded noise of NASA PIA16613 (kept here as PIA16613.jpg)
python prep_image.py PIA16613.jpg frame.png

# 2. mask: flag rendered as a 1-bit bitmap, wrapped in a CAL1 header -> mask.cal
python make_payload.py mask.cal

# 3. the shipped binary (static, stripped Linux ELF)
zig cc -target x86_64-linux-musl -O2 -s -static -o ../dist/lenscal lenscal.c -lm

# 4. encode. Any build of lenscal.c gives identical output; on Windows, build a native
#    copy to run it (it doesn't ship):
zig cc -target x86_64-windows-gnu -O2 -o lenscal_win.exe lenscal.c
./lenscal_win.exe frame.png mask.cal ../dist/condor_cal.png

# 5. verify
python ../solution/solve.py ../dist/condor_cal.png mask.png
```

`frame.png` is regenerable and not committed. To change the flag, edit `FLAG` in
`make_payload.py`, redo steps 2, 4 and 5, and update `challenge.yml` + `SOLUTION.md`
(the mask dimensions in step 6 of SOLUTION.md will change).
