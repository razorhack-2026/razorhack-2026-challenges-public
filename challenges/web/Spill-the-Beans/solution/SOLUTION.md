# Spill the Beans — Solution

**Flag:** `flag{n1c3_s3ss10n_8uddY}`

**Requirements to run `solve.py`:** `pip install requests`

## Vulnerability summary

Three small bugs chain into remote code execution:

1. **Trust-the-client authorization** (`src/app/public/modules.php`) — the engineering-only
   module loader checks `$_COOKIE['role']` with no server-side validation. Setting the `role`
   cookie to `engineer` is enough to unlock it.

2. **PHP session file poisoning** (`src/app/public/profile.php`) — the profile form stores the
   raw `display_name` POST value into `$_SESSION['display_name']` before any sanitization.
   `htmlspecialchars()` is only applied when the value is echoed back into the HTML form, so it
   never touches what actually gets written to disk. PHP's default `files` session handler
   serializes session data to a plaintext file (`session.save_path`, which the image leaves
   unset, so PHP falls back to `sys_get_temp_dir()` → `/tmp/sess_<PHPSESSID>`). A display name of
   `<?php system($_GET['c']); ?>` ends up verbatim inside that file.

3. **Local File Inclusion via an unfiltered path** (`src/app/public/modules.php`) — the module
   loader builds `include($modulesDir . $module)` directly from the `module` query parameter,
   with no filtering at all. A plain `../../../` traversal reaches up and out of
   `/var/www/html-modules/` (which is outside the webroot specifically to *look* hardened) to
   `/tmp/sess_<PHPSESSID>`.

`include()` executes any `<?php ... ?>` tags found in the included file regardless of its name
or extension, so including our own poisoned session file runs our payload as PHP — a full
web shell, which we use to read the `FLAG` environment variable.

## Step-by-step

1. Request the app once (or just note that PHP will mint a `PHPSESSID` on first contact) and set
   a `role=engineer` cookie — it's never checked against anything server-side.
2. `POST /profile.php` with `display_name=<?php system($_GET['c']); ?>`. This gets serialized
   into `/tmp/sess_<PHPSESSID>` on disk.
3. `GET /modules.php?module=../../../tmp/sess_<PHPSESSID>&c=env` (with the `role` and
   `PHPSESSID` cookies attached) — a plain traversal reaches `/tmp/sess_<PHPSESSID>` from
   `/var/www/html-modules/`, since the loader does no filtering on `module`.
4. The included session file executes the planted `system($_GET['c'])` call; `c=env` dumps the
   container's environment, including `FLAG=...`.

The `diagnostics` module (a legitimate module, reachable the same way once `role=engineer` is
set) exists as an in-game hint: it prints `sys_get_temp_dir()`, pointing solvers at `/tmp` as the
session storage location without having to already know PHP's default.

Run `solution/solve.py <url>` for the full automated chain.
