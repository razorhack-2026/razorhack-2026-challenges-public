<?php
session_start();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Stored as-is. htmlspecialchars() is applied when we echo it back below,
    // so the page itself never reflects raw markup - but the raw value is
    // still what gets written into the session store on disk.
    $_SESSION['display_name'] = $_POST['display_name'] ?? '';
}

$name = $_SESSION['display_name'] ?? '';
?>
<!doctype html>
<html>
<head>
    <title>Operator Profile</title>
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
    <a href="modules.php">Console Modules</a>
    <a href="profile.php" class="active">Operator Profile</a>
</nav>

<h2>Operator Profile</h2>
<div class="profile-container">
    <img src="astronaut.png" alt="Operator portrait" class="profile-picture">
    <form method="post">  <!-- name is saved in the php session -->
        <label>Display name:
            <input type="text" name="display_name" value="<?= htmlspecialchars($name, ENT_QUOTES) ?>">
        </label>
        <button type="submit">Save</button>
    </form>
</div>
</body>
</html>
