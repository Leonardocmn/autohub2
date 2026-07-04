<?php

function db(): PDO
{
    static $pdo = null;
    if ($pdo instanceof PDO) {
        return $pdo;
    }

    global $config;
    $db = $config['db'];
    if (($db['connection'] ?? 'mysql') === 'sqlite') {
        $path = (string) $db['database'];
        if (!str_contains($path, ':') && !str_starts_with($path, DIRECTORY_SEPARATOR)) {
            $path = dirname(__DIR__) . '/' . $path;
        }
        $dir = dirname($path);
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }
        $pdo = new PDO('sqlite:' . $path, null, null, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
        $pdo->sqliteCreateFunction('NOW', static fn () => date('Y-m-d H:i:s'));
        return $pdo;
    }

    $dsn = sprintf(
        'mysql:host=%s;dbname=%s;charset=%s',
        $db['host'],
        $db['name'],
        $db['charset']
    );

    $pdo = new PDO($dsn, $db['user'], $db['pass'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);

    return $pdo;
}

function db_is_sqlite(): bool
{
    global $config;
    return (($config['db']['connection'] ?? 'mysql') === 'sqlite');
}
