<?php
session_start();

$name = $_SESSION['display_name'] ?? '';

// Engineering tools stay locked down for regular crew. Role is just read
// straight off the cookie set at first visit - there's no server-side
// account system backing it, so it's trivial to flip client-side.
$role = $_COOKIE['role'] ?? 'crew';
if ($role !== 'engineer') {
    http_response_code(403); ?>
<!doctype html>
<html>
<head>
    <title>Access Denied</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
<div class="user-badge">
    <span class="user-badge-name"><?= htmlspecialchars($name !== '' ? $name : 'Operator', ENT_QUOTES) ?></span>
    <img src="astronaut.png" alt="Operator portrait" class="user-badge-avatar">
</div>
<h1>RPC Drill Rig Console</h1>
<nav class="console-nav">
    <a href="index.php">Console</a>
    <a href="modules.php" class="active">Console Modules</a>
    <a href="profile.php">Operator Profile</a>
</nav>

<div class="access-denied">
    <h2>Access Denied</h2>
    <p>[ ERROR 403 ] Engineering clearance required to load rig modules.</p>
    <p>Contact your shift lead if you believe this is in error.</p>
</div>
</body>
</html>
<?php
    exit;
}

// Modules live outside the public webroot so they can't be requested
// directly over HTTP - only this loader can reach them.
$modulesDir = '/var/www/html-modules/';
$module = $_GET['module'] ?? 'home.php';

$installedModules = [
    'Home' => 'home.php',
    'Diagnostics' => 'diagnostics.php',
    'Comms' => 'comms.php',
    'Drill Log' => 'drill_log.php',
    'Secrets' => 'secrets.php',
];

$path = $modulesDir . $module;
?>
<!doctype html>
<html>
<head>
    <title>Modules</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
<div class="user-badge">
    <span class="user-badge-name"><?= htmlspecialchars($name !== '' ? $name : 'Operator', ENT_QUOTES) ?></span>
    <img src="astronaut.png" alt="Operator portrait" class="user-badge-avatar">
</div>
<h1>RPC Drill Rig Console</h1>
<nav class="console-nav">
    <a href="index.php">Console</a>
    <a href="modules.php" class="active">Console Modules</a>
    <a href="profile.php">Operator Profile</a>
</nav>

<h2>Installed Modules</h2>
<ul class="module-list">
<?php foreach ($installedModules as $label => $file): ?>
    <li>
        <a href="modules.php?module=<?= urlencode($file) ?>"
           class="<?= $file === $module ? 'active' : '' ?>">
            <?= htmlspecialchars($label, ENT_QUOTES) ?>
        </a>
    </li>
<?php endforeach; ?>
</ul>

<div class="module-output">
<?php
if (!is_readable($path)) {
    http_response_code(404);
    echo "<p>Module not found: " . htmlspecialchars($module, ENT_QUOTES) . "</p>";
} else {
    include $path;
}
?>
</div>
</body>
</html>
