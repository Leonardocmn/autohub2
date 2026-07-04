<?php

$basePath = require __DIR__ . '/autohub_path.php';
require_once $basePath . '/app/bootstrap.php';

$path = current_path();
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$settings = new SettingsRepository(db());
$aiService = static function () use ($settings): AIService {
    return new AIService(
        new AITaskRouter($settings),
        new AIProviderFactory($settings),
        new AILogger(db())
    );
};

if ($path === '/webhook/evolution' && $method === 'POST') {
    $processor = new WebhookProcessor(
        db(),
        new EvolutionClient($settings),
        $aiService()
    );
    json_response($processor->handle(request_json()));
}

if ($path === '/login') {
    $error = '';
    if ($method === 'POST') {
        verify_csrf();
        if (attempt_login(post_value('email'), post_value('password'))) {
            redirect('/');
        }
        $error = 'E-mail ou senha invalidos.';
    }
    require $basePath . '/app/views/login.php';
    exit;
}

if ($path === '/logout') {
    logout();
    redirect('/login');
}

require_auth();

if ($path === '/') {
    $title = 'Ofertas';
    $offers = db()->query('SELECT * FROM offers ORDER BY id DESC LIMIT 100')->fetchAll();
    require $basePath . '/app/views/offers.php';
    exit;
}

if ($path === '/admins') {
    $title = 'Administradores';
    if ($method === 'POST') {
        verify_csrf();
        if (post_value('action') === 'create') {
            $sql = db_is_sqlite()
                ? 'INSERT INTO admins (name, phone, active, created_at)
                   VALUES (?, ?, 1, NOW())
                   ON CONFLICT(phone) DO UPDATE SET name = excluded.name, active = 1, updated_at = NOW()'
                : 'INSERT INTO admins (name, phone, active, created_at)
                   VALUES (?, ?, 1, NOW())
                   ON DUPLICATE KEY UPDATE name = VALUES(name), active = 1, updated_at = NOW()';
            $stmt = db()->prepare($sql);
            $stmt->execute([post_value('name'), normalize_phone(post_value('phone'))]);
            flash('Administrador salvo.');
        }
        if (post_value('action') === 'toggle') {
            $stmt = db()->prepare('UPDATE admins SET active = 1 - active, updated_at = NOW() WHERE id = ?');
            $stmt->execute([(int) post_value('id')]);
            flash('Status atualizado.');
        }
        redirect('/admins');
    }
    $admins = db()->query('SELECT * FROM admins ORDER BY name')->fetchAll();
    require $basePath . '/app/views/admins.php';
    exit;
}

if ($path === '/buyers') {
    $title = 'Compradores';
    if ($method === 'POST') {
        verify_csrf();
        if (post_value('action') === 'create') {
            $sql = db_is_sqlite()
                ? 'INSERT INTO buyers (name, phone, active, created_at)
                   VALUES (?, ?, 1, NOW())
                   ON CONFLICT(phone) DO UPDATE SET name = excluded.name, active = 1, updated_at = NOW()'
                : 'INSERT INTO buyers (name, phone, active, created_at)
                   VALUES (?, ?, 1, NOW())
                   ON DUPLICATE KEY UPDATE name = VALUES(name), active = 1, updated_at = NOW()';
            $stmt = db()->prepare($sql);
            $stmt->execute([post_value('name'), normalize_phone(post_value('phone'))]);
            flash('Comprador salvo.');
        }
        if (post_value('action') === 'toggle') {
            $stmt = db()->prepare('UPDATE buyers SET active = 1 - active, updated_at = NOW() WHERE id = ?');
            $stmt->execute([(int) post_value('id')]);
            flash('Status atualizado.');
        }
        redirect('/buyers');
    }
    $buyers = db()->query('SELECT * FROM buyers ORDER BY name')->fetchAll();
    require $basePath . '/app/views/buyers.php';
    exit;
}

if ($path === '/settings') {
    $title = 'Configuracoes';
    if ($method === 'POST') {
        verify_csrf();
        $action = post_value('action');

        if ($action === 'save_evolution') {
            if (post_value('evolution_api_url')) {
                $settings->set('EVOLUTION_API_URL', rtrim(post_value('evolution_api_url'), '/'));
            }
            if (post_value('evolution_instance_name')) {
                $settings->set('EVOLUTION_INSTANCE_NAME', post_value('evolution_instance_name'));
            }
            if (post_value('evolution_api_key')) {
                $settings->set('EVOLUTION_API_KEY', post_value('evolution_api_key'));
            }
            flash('Configuracao Evolution salva.');
        }

        if ($action === 'save_ai') {
            if (post_value('ai_default_provider')) {
                $settings->set('AI_DEFAULT_PROVIDER', post_value('ai_default_provider'));
            }
            if (post_value('ai_model')) {
                $settings->set('AI_MODEL', post_value('ai_model'));
                $settings->set('OPENAI_MODEL', post_value('ai_model'));
            }
            if (post_value('ai_api_key')) {
                $settings->set('AI_API_KEY', post_value('ai_api_key'));
                $settings->set('OPENAI_API_KEY', post_value('ai_api_key'));
            }
            $settings->set('AI_TEMPERATURE', post_value('ai_temperature', '0.2'));
            $settings->set('AI_MAX_TOKENS', post_value('ai_max_tokens', '900'));
            $settings->set('AI_TIMEOUT_SECONDS', post_value('ai_timeout_seconds', '60'));
            $settings->set('AI_MAX_RETRIES', post_value('ai_max_retries', '1'));
            flash('Configuracao do AIService salva.');
        }

        if ($action === 'test_evolution') {
            $test = (new EvolutionClient($settings))->testConnection();
            flash($test['success'] ? 'Evolution conectada: ' . ($test['status'] ?? 'ok') : ($test['error'] ?? 'Falha na Evolution'), $test['success'] ? 'success' : 'danger');
        }

        if ($action === 'test_ai') {
            $test = $aiService()->testConnection(['origin' => 'admin:settings']);
            flash($test['success'] ? 'AIService conectado: ' . ($test['provider'] ?? 'ok') : ($test['error'] ?? 'Falha no AIService'), $test['success'] ? 'success' : 'danger');
        }

        redirect('/settings');
    }

    $evolutionUrl = $settings->get('EVOLUTION_API_URL', 'https://143.95.217.12');
    $evolutionInstance = $settings->get('EVOLUTION_INSTANCE_NAME', '');
    $evolutionKeyMasked = $settings->masked('EVOLUTION_API_KEY');
    $aiDefaultProvider = $settings->get('AI_DEFAULT_PROVIDER', 'openai');
    $aiModel = $settings->get('AI_MODEL', $settings->get('OPENAI_MODEL', 'gpt-4o-mini'));
    $aiKeyMasked = $settings->masked('AI_API_KEY') ?: $settings->masked('OPENAI_API_KEY');
    $aiTemperature = $settings->get('AI_TEMPERATURE', '0.2');
    $aiMaxTokens = $settings->get('AI_MAX_TOKENS', '900');
    $aiTimeoutSeconds = $settings->get('AI_TIMEOUT_SECONDS', '60');
    $aiMaxRetries = $settings->get('AI_MAX_RETRIES', '1');
    $scheme = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
    $host = $_SERVER['HTTP_HOST'] ?? 'seudominio.com';
    $webhookUrl = $scheme . '://' . $host . '/webhook/evolution';
    require $basePath . '/app/views/settings.php';
    exit;
}

if ($path === '/logs') {
    $title = 'Logs de envio';
    $logs = db()->query(
        'SELECT send_logs.*, buyers.name AS buyer_name
         FROM send_logs
         LEFT JOIN buyers ON buyers.id = send_logs.buyer_id
         ORDER BY send_logs.id DESC
         LIMIT 300'
    )->fetchAll();
    $aiLogs = db()->query(
        'SELECT *
         FROM ai_logs
         ORDER BY id DESC
         LIMIT 100'
    )->fetchAll();
    require $basePath . '/app/views/logs.php';
    exit;
}

http_response_code(404);
echo 'Pagina nao encontrada.';
