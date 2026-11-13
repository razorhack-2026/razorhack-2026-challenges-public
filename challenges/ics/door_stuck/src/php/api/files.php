<?php
require_once __DIR__ . '/../includes/bootstrap.php';
require_authentication();

$files = [
    'CARGO_BAY_12_MANUAL.pdf',
    'cargo_bay_traffic.pcap',
    'SHIFT_BRIEF_244.txt',
];
sort($files, SORT_STRING);
$entries = [];
foreach ($files as $name) {
    $entries[] = [
        'name' => $name,
        'download' => '/api/download.php?file=' . rawurlencode($name),
    ];
}

json_response(['success' => true, 'files' => $entries]);
