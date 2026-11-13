<?php
require_once __DIR__ . '/../classes/ArchiveWriter.php';
require_once __DIR__ . '/../classes/EmailNotifier.php';
require_once __DIR__ . '/../classes/Form.php';

$forms = [];
if (isset($_COOKIE['forms'])) {
    $raw = base64_decode($_COOKIE['forms'], true);
    $decoded = $raw !== false ? @unserialize($raw) : false;
    if (is_array($decoded)) {
        $forms = $decoded;
    }
}
