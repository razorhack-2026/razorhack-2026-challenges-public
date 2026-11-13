<?php
require_once __DIR__ . '/../includes/bootstrap.php';
require_authentication();

$assets = [
    'NoAlarms.mp4' => __DIR__ . '/../../assets/video/NoAlarms.mp4',
    'PressureAlarm.mp4' => __DIR__ . '/../../assets/video/PressureAlarm.mp4',
    'PressureContainerAlarm.mp4' => __DIR__ . '/../../assets/video/PressureContainerAlarm.mp4',
    'Lights.mp4' => __DIR__ . '/../../assets/video/Lights.mp4',
    'DoorClosed.mp4' => __DIR__ . '/../../assets/video/DoorClosed.mp4',
];
$name = $_GET['file'] ?? '';
if (!is_string($name) || !isset($assets[$name]) || !is_file($assets[$name])) {
    http_response_code(404);
    exit;
}

$path = $assets[$name];
$size = filesize($path);
$start = 0;
$end = $size - 1;
if (isset($_SERVER['HTTP_RANGE']) &&
    preg_match('/^bytes=(\d*)-(\d*)$/', $_SERVER['HTTP_RANGE'], $range)) {
    if ($range[1] === '' && $range[2] !== '') {
        $suffixLength = (int)$range[2];
        if ($suffixLength > 0) {
            $start = max(0, $size - $suffixLength);
        }
    } elseif ($range[1] !== '') {
        $start = (int)$range[1];
        if ($range[2] !== '') {
            $end = min((int)$range[2], $size - 1);
        }
    }
    if ($start > $end || $start >= $size) {
        http_response_code(416);
        header("Content-Range: bytes */$size");
        exit;
    }
    http_response_code(206);
    header("Content-Range: bytes $start-$end/$size");
}

$length = $end - $start + 1;
header('Content-Type: video/mp4');
header('Accept-Ranges: bytes');
header('Content-Length: ' . $length);
header('Cache-Control: private, no-store');
header('X-Content-Type-Options: nosniff');
if ($_SERVER['REQUEST_METHOD'] === 'HEAD') {
    exit;
}

$file = fopen($path, 'rb');
if ($file === false) {
    http_response_code(500);
    exit;
}
fseek($file, $start);
while ($length > 0 && !feof($file)) {
    $chunk = fread($file, min(8192, $length));
    if ($chunk === false || $chunk === '') {
        break;
    }
    echo $chunk;
    $length -= strlen($chunk);
}
fclose($file);
