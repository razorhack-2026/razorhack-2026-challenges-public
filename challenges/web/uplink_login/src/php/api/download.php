<?php
require_once __DIR__ . '/../includes/bootstrap.php';
require_authentication();

$allowedFiles = [
    'CARGO_BAY_12_MANUAL.pdf' => __DIR__ . '/../../assets/documents/CARGO_BAY_12_MANUAL.pdf',
    'cargo_bay_traffic.pcap' => __DIR__ . '/../../assets/network/cargo_bay_traffic.pcap',
    'SHIFT_BRIEF_244.txt' => __DIR__ . '/../../assets/documents/SHIFT_BRIEF_244.txt',
];
$name = $_GET['file'] ?? '';
if (!is_string($name) || !isset($allowedFiles[$name]) || !is_file($allowedFiles[$name])) {
    http_response_code(404);
    exit;
}

$path = $allowedFiles[$name];
$contentTypes = [
    'CARGO_BAY_12_MANUAL.pdf' => 'application/pdf',
    'cargo_bay_traffic.pcap' => 'application/vnd.tcpdump.pcap',
    'SHIFT_BRIEF_244.txt' => 'text/plain; charset=utf-8',
];
header('Content-Type: ' . $contentTypes[$name]);
header('Content-Length: ' . filesize($path));
header('Content-Disposition: attachment; filename="' . $name . '"');
header('X-Content-Type-Options: nosniff');
readfile($path);
