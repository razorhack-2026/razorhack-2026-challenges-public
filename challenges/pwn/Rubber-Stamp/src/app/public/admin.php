<?php
$remoteAddr = $_SERVER['REMOTE_ADDR'] ?? '';
$isInternal = in_array($remoteAddr, ['127.0.0.1', '::1'], true);

if (!$isInternal) {
    http_response_code(403);
    ?>
<!doctype html>
<html>
<head>
    <title>Rubber Stamp &mdash; Access Denied</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
<div class="portal">
    <header class="portal-header">
        <img src="logo.svg" alt="" class="portal-logo">
        <div>
            <h1>Rubber Stamp</h1>
            <p class="subtitle">Interoffice Forms Portal</p>
        </div>
    </header>
    <div class="portal-body">
        <h2>Access Denied</h2>
        <p>This panel is only reachable by admins from RazerPowerCo's internal ops network.</p>
    </div>
    <footer class="portal-footer">&copy; <?= date('Y') ?> RazerPowerCo. All rights reserved.</footer>
</div>
</body>
</html>
    <?php
    exit;
}
?>
<!doctype html>
<html>
<head>
    <title>Rubber Stamp &mdash; Admin Override</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
<div class="portal">
    <header class="portal-header">
        <img src="logo.svg" alt="" class="portal-logo">
        <div>
            <h1>Rubber Stamp</h1>
            <p class="subtitle">Interoffice Forms Portal</p>
        </div>
    </header>
    <div class="portal-body">
        <h2>Admin Override</h2>
        <p>Expedited processing - bypasses the approval queue entirely:</p>
        <p class="override-code"><?= htmlspecialchars(getenv('FLAG') ?: 'NOT SET', ENT_QUOTES) ?></p>
    </div>
    <footer class="portal-footer">&copy; <?= date('Y') ?> RazerPowerCo. All rights reserved.</footer>
</div>
</body>
</html>
