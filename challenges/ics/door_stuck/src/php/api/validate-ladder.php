<?php
require_once __DIR__ . '/../includes/bootstrap.php';
require_authentication();

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    json_response(['success' => false, 'error' => 'POST required.'], 405);
}

$body = read_json_request();
$rungs = $body['rungs'] ?? null;

if (!is_array($rungs) || count($rungs) < 1 || count($rungs) > 20) {
    json_response(['success' => false, 'error' => 'Add between 1 and 20 rungs before compiling.'], 400);
}

// Normalize editor data once so each rubric check compares known contact/coil shapes.
function normalize_component(mixed $component, string $kind): ?array
{
    if (!is_array($component) ||
        ($component['kind'] ?? null) !== $kind ||
        !is_string($component['mode'] ?? null) ||
        !is_string($component['tag'] ?? null)) {
        return null;
    }

    $mode = strtoupper($component['mode']);
    $tag = strtoupper(trim($component['tag']));

    // Contacts support NO/NC. Coils support OTE/OTU.
    $allowedModes = $kind === 'contact'
        ? ['NO', 'NC']
        : ['OTE', 'OTL', 'OTU'];

    if (!in_array($mode, $allowedModes, true) ||
        !preg_match('/^[A-Z][A-Z0-9_]{0,63}$/', $tag)) {
        return null;
    }

    return ['kind' => $kind, 'mode' => $mode, 'tag' => $tag];
}

$program = [];

foreach ($rungs as $rung) {
    if (!is_array($rung) ||
        !is_array($rung['components'] ?? null) ||
        !is_array($rung['branches'] ?? [])) {
        json_response(['success' => false, 'error' => 'Program contains an incomplete rung.'], 400);
    }

    $mainPath = [];

    foreach ($rung['components'] as $component) {
        $kind = is_array($component) ? ($component['kind'] ?? '') : '';
        $normalized = normalize_component(
            $component,
            $kind === 'coil' ? 'coil' : 'contact'
        );

        if ($normalized === null) {
            json_response(['success' => false, 'error' => 'Program contains an unsupported contact or coil.'], 400);
        }

        $mainPath[] = $normalized;
    }

    $branches = [];

    if (count($rung['branches']) > 8) {
        json_response(['success' => false, 'error' => 'A rung may contain at most 8 parallel paths.'], 400);
    }

    foreach ($rung['branches'] as $branch) {
        if (!is_array($branch) || !is_array($branch['components'] ?? null) ||
            count($branch['components']) < 1 || count($branch['components']) > 8) {
            json_response(['success' => false, 'error' => 'Each parallel path needs at least one component.'], 400);
        }

        $path = [];

        foreach ($branch['components'] as $component) {
            $kind = is_array($component) ? ($component['kind'] ?? '') : '';

            $normalized = normalize_component(
                $component,
                $kind === 'coil' ? 'coil' : 'contact'
            );

            if ($normalized === null) {
                json_response(['success' => false, 'error' => 'Parallel paths contain an unsupported component.'], 400);
            }

            $path[] = $normalized;
        }

        $branches[] = $path;
    }

    $coils = array_keys(array_filter(
    $mainPath,
    static fn(array $item): bool => $item['kind'] === 'coil'
    ));

    if (count($coils) !== 1 || $coils[0] !== count($mainPath) - 1) {
        json_response(['success' => false, 'error' => 'Each rung needs one output coil at its right end.'], 400);
    }

    foreach ($branches as $branch) {
        $branchCoils = array_filter(
            $branch,
            static fn(array $item): bool => $item['kind'] === 'coil'
        );

        if (count($branchCoils) > 1) {
            json_response(['success' => false, 'error' => 'Each parallel path may contain at most one output coil.'], 400);
        }
    }

    $program[] = ['main' => $mainPath, 'branches' => $branches];
}

// Match a rung, including its required coil mode.
function rung_matches(
    array $rung,
    string $coilTag,
    array $mainContacts,
    array $branchContacts = [],
    string $coilMode = 'OTE'
): bool {
    $main = $rung['main'];
    $coil = array_pop($main);

    if ($coil['tag'] !== $coilTag ||
        $coil['mode'] !== $coilMode ||
        count($main) !== count($mainContacts) ||
        count($rung['branches']) !== count($branchContacts)) {
        return false;
    }

    foreach ($mainContacts as $index => $expected) {
        if ($main[$index]['tag'] !== $expected[0] ||
            $main[$index]['mode'] !== $expected[1]) {
            return false;
        }
    }

    foreach ($branchContacts as $index => $expectedPath) {
        $actualPath = $rung['branches'][$index];

        if (count($actualPath) !== count($expectedPath)) {
            return false;
        }

        foreach ($expectedPath as $contactIndex => $expected) {
            if ($actualPath[$contactIndex]['tag'] !== $expected[0] ||
                $actualPath[$contactIndex]['mode'] !== $expected[1]) {
                return false;
            }
        }
    }

    return true;
}

function has_rung(
    array $program,
    string $coil,
    array $contacts,
    array $branches = [],
    string $coilMode = 'OTE'
): bool {
    foreach ($program as $rung) {
        if (rung_matches($rung, $coil, $contacts, $branches, $coilMode)) {
            return true;
        }
    }

    return false;
}

function has_sensor_coil_pair(
    array $program,
    string $sensor,
    string $coil
): bool {
    return has_rung($program, $coil, [[$sensor, 'NO']]);
}

// Parallel paths are logically unordered, so validate the required NC contacts as a set.

function has_pressure_rung(array $program): bool
{
    $expectedTags = ['DOOR_1', 'DOOR_2', 'DOOR_3'];

    // OPTION 1: One rung with three parallel NC door contacts.
    foreach ($program as $rung) {
        $main = $rung['main'];
        $coil = array_pop($main);

        if ($coil['tag'] !== 'PRESSURE_ALARM_0_WRITE' ||
            $coil['mode'] !== 'OTE' ||
            count($rung['branches']) !== 2 ||
            count($main) !== 1 ||
            count($rung['branches'][0]) !== 1 ||
            count($rung['branches'][1]) !== 1) {
            continue;
        }

        $contacts = [
            $main[0],
            $rung['branches'][0][0],
            $rung['branches'][1][0]
        ];

        $tags = [];

        foreach ($contacts as $contact) {
            if ($contact['kind'] !== 'contact' ||
                $contact['mode'] !== 'NC') {
                continue 2;
            }

            $tags[] = $contact['tag'];
        }

        sort($tags);

        if ($tags === $expectedTags) {
            return true;
        }
    }

    // OPTION 2: Three separate rungs, one per door contact.
    $foundDoors = [];

    foreach ($program as $rung) {
        if (count($rung['branches']) !== 0) {
            continue;
        }

        $main = $rung['main'];
        $coil = array_pop($main);

        if ($coil['kind'] !== 'coil' ||
            $coil['tag'] !== 'PRESSURE_ALARM_0_WRITE' ||
            $coil['mode'] !== 'OTE' ||
            count($main) !== 1) {
            continue;
        }

        $contact = $main[0];

        if ($contact['kind'] !== 'contact' ||
            $contact['mode'] !== 'NC' ||
            !in_array($contact['tag'], $expectedTags, true)) {
            continue;
        }

        $foundDoors[] = $contact['tag'];
    }

    // All three distinct door contacts must be represented.
    $foundDoors = array_unique($foundDoors);

    sort($foundDoors);

    return $foundDoors === $expectedTags;
}



function has_lights_rung(array $program): bool
{
    $expectedLights = [
        'LIGHT_0_WRITE',
        'LIGHT_1_WRITE',
        'LIGHT_2_WRITE'
    ];

    // OPTION 1: Three separate rungs.
    $separateRungsValid = true;

    foreach ($expectedLights as $light) {
        if (!has_rung(
            $program,
            $light,
            [['SHUTDOWN_0', 'NC']]
        )) {
            $separateRungsValid = false;
            break;
        }
    }

    if ($separateRungsValid) {
        return true;
    }

    // OPTION 2: One rung with three parallel output branches.
    foreach ($program as $rung) {
        $main = $rung['main'];
        $coil = array_pop($main);

        if (count($main) !== 1 ||
            $main[0]['tag'] !== 'SHUTDOWN_0' ||
            $main[0]['mode'] !== 'NC' ||
            $coil['tag'] !== 'LIGHT_0_WRITE' ||
            $coil['mode'] !== 'OTE' ||
            count($rung['branches']) !== 2) {
            continue;
        }

        $branchLights = [];

        // The main-path coil is the first light output.
        $branchLights[] = $coil['tag'];

        $validBranches = true;

        foreach ($rung['branches'] as $branch) {
            if (count($branch) !== 1 ||
                $branch[0]['kind'] !== 'coil' ||
                $branch[0]['mode'] !== 'OTE') {
                $validBranches = false;
                break;
            }

            $branchLights[] = $branch[0]['tag'];
        }

        if (!$validBranches) {
            continue;
        }

        sort($branchLights);
        $sortedExpected = $expectedLights;
        sort($sortedExpected);

        if ($branchLights === $sortedExpected) {
            return true;
        }
    }

    return false;
}


// Server-side progress prevents clients from choosing or skipping the next challenge.
$completed = $_SESSION['completed_challenges'] ?? [];
$completed = is_array($completed) ? $completed : [];

$challengeKeys = ['camera', 'pressure', 'container', 'lights', 'door'];
$challengeIndex = count($completed);

if (!isset($challengeKeys[$challengeIndex])) {
    json_response(['success' => false, 'error' => 'All PLC restoration tasks are already complete.'], 409);
}

$challenge = $challengeKeys[$challengeIndex];

$valid = match ($challenge) {
    'camera' => has_rung(
        $program,
        'CAMERA_0_WRITE',
        [['SHUTDOWN_0', 'NC']]
    ),

    'pressure' => has_pressure_rung($program),

    'container' =>
        has_sensor_coil_pair($program, 'SENSOR_0', 'CONTAINER_ALARM_0_WRITE') &&
        has_sensor_coil_pair($program, 'SENSOR_1', 'CONTAINER_ALARM_1_WRITE') &&
        has_sensor_coil_pair($program, 'SENSOR_2', 'CONTAINER_ALARM_2_WRITE'),

    'lights' => has_lights_rung($program),

    // FINAL CHALLENGE: Require an OTU coil for DOOR_3_COMMAND.
    'door' => has_rung($program, 'DOOR_3_COMMAND', [['DOOR_3', 'NO']], [], 'OTU'),
};

if (!$valid) {
    json_response([
        'success' => false,
        'error' => 'Program not verified.',
    ]);
}

$flags = require __DIR__ . '/../includes/flags.php';

$_SESSION['completed_challenges'][] = $challenge;

json_response([
    'success' => true,
    'message' => 'Program verified and running.',
    'challenge' => $challenge,
    'flag' => $flags[$challenge] ?? null,
    'next' => $challengeIndex < count($challengeKeys) - 1,
    'earnedFlags' => array_map(
        static fn($key) => [
            'challenge' => $key,
            'flag' => $flags[$key] ?? null
        ],
        $_SESSION['completed_challenges']
    )
]);