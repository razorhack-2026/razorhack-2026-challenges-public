# GM notes: Deep Tissue

This is the 3D follow-up to Odd Pixel. Each scan is generated from a fresh procedural brain phantom, with a thin skull boundary, paired low-density ventricles, normal calcifications, and one low-contrast spherical lesion in brain tissue. Individual voxels and layers are noisy; the reference solver fetches the volume, smooths it, and selects the outlier while excluding the skull, ventricles, and calcifications.

The service requires Python and NumPy (`python -m pip install -r requirements.txt` for local verification). Run `docker compose up --build` from this folder to start it on port 8000. Compose sets `FLAG`; keep that value in sync with `challenge.yml`. The default exposure window is 30 seconds to leave room for network transfer of the full scan; `TIME_LIMIT` can be set by the deployment environment.

Run `python solution/test_server.py` from this folder to solve a fresh scan end to end and check wrong, reused, expired, malformed, oversized, and invalid-token requests. The verifier compares the recovered value with `challenge.yml` and emits no flag values.

`preview/layer.png` is an organizer-only brain-layer preview. Keep it in `solution/`; it must never be copied to `dist/` or linked from the player README.
