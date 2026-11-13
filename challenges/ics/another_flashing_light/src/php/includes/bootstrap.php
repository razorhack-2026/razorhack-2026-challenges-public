<?php

// Shared session and JSON helpers for every authenticated API route.
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_set_cookie_params([
        'lifetime' => 0,
        'path' => '/',
        'httponly' => true,
        'samesite' => 'Lax',
        'secure' => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
    ]);
    session_start();
}

function json_response(array $data, int $status = 200): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_SLASHES);
    exit;
}

function require_authentication(): void
{
    if (empty($_SESSION['authenticated'])) {
        json_response(['success' => false, 'error' => 'Authentication required.'], 401);
    }
}

function read_json_request(): array
{
    $body = json_decode(file_get_contents('php://input'), true);
    if (!is_array($body)) {
        json_response(['success' => false, 'error' => 'A valid JSON request is required.'], 400);
    }
    return $body;
}

function voice_log_path(): string
{
    $configuredPath = getenv('CARGO_BAY_VOICE_LOG');
    return is_string($configuredPath) && $configuredPath !== ''
        ? $configuredPath
        : __DIR__ . '/../../assets/audio/SHIFT_LOG_243.mp3';
}
