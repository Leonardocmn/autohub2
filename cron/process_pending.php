<?php

declare(strict_types=1);

require_once __DIR__ . '/../app/bootstrap.php';

$settings = new SettingsRepository(db());
$processor = new WebhookProcessor(
    db(),
    new EvolutionClient($settings),
    new AIService(
        new AITaskRouter($settings),
        new AIProviderFactory($settings),
        new AILogger(db())
    )
);

$result = $processor->processPending(45);
app_log('info', 'Cron process_pending executed', $result);

echo json_encode($result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . PHP_EOL;
