<?php

function app_log(string $level, string $message, array $context = []): void
{
    $dir = dirname(__DIR__) . '/storage/logs';
    if (!is_dir($dir)) {
        mkdir($dir, 0755, true);
    }
    $line = json_encode([
        'time' => date('c'),
        'level' => $level,
        'message' => $message,
        'context' => $context,
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    file_put_contents($dir . '/app-' . date('Y-m-d') . '.log', $line . PHP_EOL, FILE_APPEND);
}

