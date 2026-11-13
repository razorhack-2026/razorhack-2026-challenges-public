<?php
require_once __DIR__ . '/../includes/bootstrap.php';
require_authentication();

json_response([
    'authenticated' => true,
    'crew_id' => $_SESSION['crew_id'] ?? 'CREW-0000',
]);
