<?php

declare(strict_types=1);

session_start();
date_default_timezone_set('America/Sao_Paulo');

$config = require __DIR__ . '/config.php';

require_once __DIR__ . '/helpers.php';
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/auth.php';
require_once __DIR__ . '/logger.php';
require_once __DIR__ . '/repositories/SettingsRepository.php';
require_once __DIR__ . '/services/EvolutionClient.php';
require_once __DIR__ . '/services/AI/DTO/AIRequest.php';
require_once __DIR__ . '/services/AI/DTO/AIResponse.php';
require_once __DIR__ . '/services/AI/Contracts/AIProviderInterface.php';
require_once __DIR__ . '/services/AI/Prompts/AIPromptRegistry.php';
require_once __DIR__ . '/services/AI/AISanitizer.php';
require_once __DIR__ . '/services/AI/AITaskRouter.php';
require_once __DIR__ . '/services/AI/AIProviderFactory.php';
require_once __DIR__ . '/services/AI/AILogger.php';
require_once __DIR__ . '/services/AI/Providers/OpenAIProvider.php';
require_once __DIR__ . '/services/AI/Providers/NullAIProvider.php';
require_once __DIR__ . '/services/AI/AIService.php';
require_once __DIR__ . '/services/WebhookProcessor.php';

set_exception_handler(function (Throwable $e) use ($config): void {
    app_log('fatal', $e->getMessage(), ['trace' => $e->getTraceAsString()]);
    http_response_code(500);
    if ($config['app_debug']) {
        echo '<pre>' . h($e->getMessage() . "\n" . $e->getTraceAsString()) . '</pre>';
        return;
    }
    echo 'Erro interno. Verifique os logs.';
});
