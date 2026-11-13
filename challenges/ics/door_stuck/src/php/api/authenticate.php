<?php
require_once __DIR__ . '/../includes/bootstrap.php';

// Correct password
$PASS = 'ST4RS';

$SOLUTION_COORDS = [[2, 1], [5, 3], [0, 5], [6, 0], [3, 6]];

// ── basic rate limiting using a flat file keyed by IP ──
$rateFile = sys_get_temp_dir() . '/ctf_attempts.json';
$ip = $_SERVER['REMOTE_ADDR'];
$now = time();
$windowSeconds = 60;
$maxAttempts = 10;

$attempts = file_exists($rateFile) ? json_decode(file_get_contents($rateFile), true) : [];
$entry = $attempts[$ip] ?? ['count' => 0, 'resetAt' => $now + $windowSeconds];

if ($now > $entry['resetAt']) {
    $entry = ['count' => 0, 'resetAt' => $now + $windowSeconds];
}

if ($entry['count'] >= $maxAttempts) {
    http_response_code(429);
    json_response(['success' => false, 'error' => 'Too many attempts. Try again shortly.'], 429);
}

$entry['count']++;
$attempts[$ip] = $entry;
file_put_contents($rateFile, json_encode($attempts));

// ── the actual check ──
$body = json_decode(file_get_contents('php://input'), true);
if (!is_array($body)) {
    $body = [];
}
$pass = $body['pass'] ?? '';

if (is_string($pass) && hash_equals($PASS, $pass)) {
    session_regenerate_id(true);
    $_SESSION['authenticated'] = true;
    $_SESSION['crew_id'] = isset($body['user']) && is_string($body['user'])
        ? $body['user']
        : 'CREW-0000';
    json_response(['success' => true, 'highlight' => $SOLUTION_COORDS]);
} else {
    json_response(['success' => false]);
}