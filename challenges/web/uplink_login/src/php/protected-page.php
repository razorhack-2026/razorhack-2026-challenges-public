<?php
require_once __DIR__ . '/includes/bootstrap.php';

if (empty($_SESSION['authenticated'])) {
    header('Location: /');
    exit;
}

$pages = ['ladder-editor', 'cameras', 'files'];
$page = $_GET['page'] ?? '';
if (!is_string($page) || !in_array($page, $pages, true)) {
    http_response_code(404);
    exit;
}

require __DIR__ . '/../html/' . $page . '.html';
