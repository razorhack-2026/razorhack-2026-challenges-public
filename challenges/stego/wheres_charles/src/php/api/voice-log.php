<?php
require_once __DIR__ . '/../includes/bootstrap.php';
require_authentication();

$path = voice_log_path();
if (!is_file($path)) {
    http_response_code(404);
    exit;
}

header('Content-Type: audio/mpeg');
header('Content-Length: ' . filesize($path));
header('Content-Disposition: inline; filename="SHIFT_LOG_243.mp3"');
header('X-Content-Type-Options: nosniff');
readfile($path);
