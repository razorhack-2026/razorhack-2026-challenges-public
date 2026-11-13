<?php
require_once __DIR__ . '/bootstrap.php';

$fieldSchemas = [
    'Form 27-A: Expense Reimbursement' => [
        ['key' => 'amount', 'label' => 'Amount', 'type' => 'text'],
        ['key' => 'expense_description', 'label' => 'Expense Description', 'type' => 'textarea'],
    ],
    'Form 28-B: Supply Requisition' => [
        ['key' => 'item', 'label' => 'Item', 'type' => 'text'],
        ['key' => 'justification', 'label' => 'Justification', 'type' => 'textarea'],
    ],
    'Form 8-A: Leave Request' => [
        ['key' => 'start_date', 'label' => 'Start Date', 'type' => 'date'],
        ['key' => 'end_date', 'label' => 'End Date', 'type' => 'date'],
        ['key' => 'reason', 'label' => 'Reason', 'type' => 'textarea'],
    ],
    'Form 2-C: Maintenance Ticket' => [
        ['key' => 'location', 'label' => 'Location', 'type' => 'text'],
        ['key' => 'issue', 'label' => 'Issue Description', 'type' => 'textarea'],
        ['key' => 'priority', 'label' => 'Priority', 'type' => 'select', 'options' => ['Low', 'Medium', 'High']],
    ],

];

if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'create') {
    $formType = $_POST['form_type'] ?? '';
    $schema = $fieldSchemas[$formType] ?? null;

    if ($schema !== null) {
        $formId = 'FORM-' . substr(sha1(uniqid('', true)), 0, 6);
        $fields = [];
        foreach ($schema as $fieldDef) {
            $fields[$fieldDef['key']] = $_POST['fields'][$fieldDef['key']] ?? '';
        }

        $auditLog = new ArchiveWriter('/var/log/rubberstamp/audit.log');
        $forms[] = new Form($formId, $formType, $fields, $auditLog);

        $notifier = new EmailNotifier();
        $notifier->recipient = 'finance@razorpowerco.sys';
        $notifier->subject = "New {$formType} submitted: {$formId}";
        unset($notifier); // notifies (logs) on teardown

        setcookie('forms', base64_encode(serialize($forms)), time() + 86400 * 30, '/');
    }

    // Redirect after processing so refreshing the result page doesn't
    // resubmit the form and add another entry.
    header('Location: index.php');
    exit;
}

$selectedType = $_GET['type'] ?? '';
$selectedSchema = $fieldSchemas[$selectedType] ?? null;
?>
<!doctype html>
<html>
<head>
    <title>Rubber Stamp &mdash; Submit a Form</title>
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
            <a href="index.php">My Forms</a>
            <a href="submit.php" class="active">Submit a Form</a>
        </nav>

        <h2>Submit a Form</h2>
        <form method="get" class="submission-form">
            <label>Form Type
                <select name="type" onchange="this.form.submit()">
                    <option value="" disabled<?= $selectedType === '' ? ' selected' : '' ?>>Select a form type&hellip;</option>
                    <?php foreach (array_keys($fieldSchemas) as $type): ?>
                    <option value="<?= htmlspecialchars($type, ENT_QUOTES) ?>"<?= $selectedType === $type ? ' selected' : '' ?>><?= htmlspecialchars($type, ENT_QUOTES) ?></option>
                    <?php endforeach; ?>
                </select>
            </label>
            <noscript><button type="submit">Choose</button></noscript>
        </form>

        <?php if ($selectedSchema !== null): ?>
        <form method="post" class="submission-form">
            <input type="hidden" name="action" value="create">
            <input type="hidden" name="form_type" value="<?= htmlspecialchars($selectedType, ENT_QUOTES) ?>">
            <?php foreach ($selectedSchema as $fieldDef): ?>
            <label><?= htmlspecialchars($fieldDef['label'], ENT_QUOTES) ?>
                <?php if ($fieldDef['type'] === 'textarea'): ?>
                <textarea name="fields[<?= htmlspecialchars($fieldDef['key'], ENT_QUOTES) ?>]" required></textarea>
                <?php elseif ($fieldDef['type'] === 'select'): ?>
                <select name="fields[<?= htmlspecialchars($fieldDef['key'], ENT_QUOTES) ?>]" required>
                    <?php foreach ($fieldDef['options'] as $option): ?>
                    <option value="<?= htmlspecialchars($option, ENT_QUOTES) ?>"><?= htmlspecialchars($option, ENT_QUOTES) ?></option>
                    <?php endforeach; ?>
                </select>
                <?php else: ?>
                <input type="<?= htmlspecialchars($fieldDef['type'], ENT_QUOTES) ?>" name="fields[<?= htmlspecialchars($fieldDef['key'], ENT_QUOTES) ?>]" required>
                <?php endif; ?>
            </label>
            <?php endforeach; ?>
            <button type="submit">Submit Form</button>
        </form>
        <?php endif; ?>
    </div>
    <footer class="portal-footer">&copy; <?= date('Y') ?> RazerPowerCo. All rights reserved.</footer>
</div>
</body>
</html>
