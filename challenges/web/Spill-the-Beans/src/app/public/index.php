<?php
session_start();

if (!isset($_COOKIE['role'])) {
    setcookie('role', 'crew', time() + 86400, '/');
}

$name = $_SESSION['display_name'] ?? '';
?>
<!doctype html>
<html>
<head>
    <title>Drill Rig Console</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
<div class="user-badge">
    <span class="user-badge-name"><?= htmlspecialchars($name !== '' ? $name : 'Operator', ENT_QUOTES) ?></span>
    <img src="astronaut.png" alt="Operator portrait" class="user-badge-avatar">
</div>
<h1>RPC Drill Rig Console</h1>
<nav class="console-nav">
    <a href="index.php" class="active">Console</a>
    <a href="modules.php">Console Modules</a>
    <a href="profile.php">Operator Profile</a>
</nav>
<h3>Welcome back, <?= htmlspecialchars($name !== '' ? $name : 'Operator', ENT_QUOTES) ?>.</h3>
<table class="data-table">
    <tr><th>Status</th><td>STANDBY (safe mode)</td></tr>
    <tr><th>Current depth</th><td>142.6 m</td></tr>
    <tr><th>Core temp</th><td>38.2&deg;C</td></tr>
    <tr><th>Power reserve</th><td>61%</td></tr>
    <tr><th>Last deployment</th><td>Cycle 4471, Sol 212</td></tr>
    <tr><th>Location Type</th><td>Asteroid</td></tr>
    <tr><th>Location Name</th><td>2000 SY178</td></tr>
</table>
</body>
</html>
