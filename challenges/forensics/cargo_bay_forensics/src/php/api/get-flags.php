<?php
require_once __DIR__ . '/../includes/bootstrap.php';
require_authentication();

$flags = require __DIR__ . '/../includes/flags.php';

$completed = $_SESSION['completed_challenges'] ?? [];
$completed = is_array($completed) ? $completed : [];

$earnedFlags = [];

foreach ($completed as $challenge) {
    if (isset($flags[$challenge])) {
        $earnedFlags[] = [
            'challenge' => $challenge,
            'flag' => $flags[$challenge]
        ];
    }
}

json_response([
    'success' => true,
    'earnedFlags' => $earnedFlags
]);
