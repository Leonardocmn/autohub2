<?php

function env_value(string $key, ?string $default = null): ?string
{
    static $env = null;
    if ($env === null) {
        $env = [];
        $path = dirname(__DIR__) . '/.env';
        if (is_file($path)) {
            foreach (file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
                $line = trim($line);
                if ($line === '' || str_starts_with($line, '#') || !str_contains($line, '=')) {
                    continue;
                }
                [$name, $value] = explode('=', $line, 2);
                $env[trim($name)] = trim($value, " \t\n\r\0\x0B\"'");
            }
        }
    }
    return $env[$key] ?? getenv($key) ?: $default;
}

return [
    'app_name' => env_value('APP_NAME', 'AutoHub MVP'),
    'app_url' => rtrim((string) env_value('APP_URL', ''), '/'),
    'app_env' => env_value('APP_ENV', 'production'),
    'app_debug' => env_value('APP_DEBUG', 'false') === 'true',
    'app_key' => env_value('APP_KEY', ''),
    'db' => [
        'connection' => env_value('DB_CONNECTION', 'mysql'),
        'database' => env_value('DB_DATABASE', dirname(__DIR__) . '/storage/local.sqlite'),
        'host' => env_value('DB_HOST', 'localhost'),
        'name' => env_value('DB_NAME', ''),
        'user' => env_value('DB_USER', ''),
        'pass' => env_value('DB_PASS', ''),
        'charset' => env_value('DB_CHARSET', 'utf8mb4'),
    ],
];
