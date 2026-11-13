<?php
require_once __DIR__ . '/../includes/bootstrap.php';
require_authentication();

$videos = ['NoAlarms.mp4', 'PressureAlarm.mp4', 'PressureContainerAlarm.mp4', 'Lights.mp4', 'DoorClosed.mp4'];

$completed = $_SESSION['completed_challenges'] ?? [];
$completed = is_array($completed) ? $completed : [];
$nextIndex = count($completed);

json_response([
    'success' => true,
    'completed' => $nextIndex,
    'total' => count($videos),
    'video' => $nextIndex > 0 ? $videos[$nextIndex - 1] : null,
]);
