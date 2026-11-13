<?php
require_once __DIR__ . '/bootstrap.php';
?>
<!doctype html>
<html>
<head>
    <title>Rubber Stamp &mdash; My Forms</title>
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
        <nav class="tabs">
            <a href="index.php" class="active">My Forms</a>
            <a href="submit.php">Submit a Form</a>
        </nav>

        <h2>My Forms</h2>
        <?php if (empty($forms)): ?>
        <p class="footnote">No forms submitted yet from this terminal.</p>
        <?php endif; ?>
        <?php foreach ($forms as $f): ?>
        <div class="form-card">
            <div class="form-card-header">
                <strong><?= htmlspecialchars($f->formId, ENT_QUOTES) ?></strong>
                <span class="form-type-badge"><?= htmlspecialchars($f->formType, ENT_QUOTES) ?></span>
                <span class="form-status"><?= htmlspecialchars($f->status, ENT_QUOTES) ?></span>
            </div>
            <?php if (is_array($f->fields)): ?>
            <dl class="form-fields">
                <?php foreach ($f->fields as $key => $value): ?>
                <dt><?= htmlspecialchars((string) $key, ENT_QUOTES) ?></dt>
                <dd><?= htmlspecialchars((string) $value, ENT_QUOTES) ?></dd>
                <?php endforeach; ?>
            </dl>
            <?php endif; ?>
        </div>
        <?php endforeach; ?>
    </div>
    <footer class="portal-footer">&copy; <?= date('Y') ?> RazerPowerCo. All rights reserved.</footer>
</div>
</body>
</html>
