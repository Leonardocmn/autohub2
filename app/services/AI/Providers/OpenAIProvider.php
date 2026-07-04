<?php

class OpenAIProvider implements AIProviderInterface
{
    private SettingsRepository $settings;

    public function __construct(SettingsRepository $settings)
    {
        $this->settings = $settings;
    }

    public function name(): string
    {
        return 'openai';
    }

    public function textCompletion(AIRequest $request): AIResponse
    {
        $apiKey = $this->apiKey();
        $model = (string) ($request->model ?: 'gpt-4o-mini');
        if (!$apiKey) {
            return new AIResponse(false, '', [], $this->name(), $model, 0, 0, 0.0, 'API Key do AIService nao configurada.');
        }

        $payload = [
            'model' => $model,
            'temperature' => $request->temperature,
            'max_tokens' => $request->maxTokens,
            'messages' => [
                ['role' => 'system', 'content' => $request->systemPrompt],
                ['role' => 'user', 'content' => $request->userPrompt],
            ],
        ];

        if (in_array($request->task, ['padronizar_descricao', 'corrigir_anuncio', 'analisar_oferta', 'extrair_dados_veiculo'], true)) {
            $payload['response_format'] = ['type' => 'json_object'];
        }

        $attempts = max(1, $request->maxRetries);
        $last = null;
        for ($attempt = 1; $attempt <= $attempts; $attempt++) {
            $last = $this->send($payload, $apiKey, $request->timeoutSeconds);
            if ($last->success || $attempt === $attempts) {
                return $last;
            }
            usleep(250000 * $attempt);
        }

        return $last ?: new AIResponse(false, '', [], $this->name(), $model, 0, 0, 0.0, 'Falha desconhecida no provedor OpenAI.');
    }

    public function visionCompletion(AIRequest $request): AIResponse
    {
        return $this->textCompletion($request);
    }

    public function testConnection(AIRequest $request): AIResponse
    {
        return $this->textCompletion($request);
    }

    private function apiKey(): string
    {
        return (string) ($this->settings->get('AI_API_KEY', '') ?: $this->settings->get('OPENAI_API_KEY', ''));
    }

    private function send(array $payload, string $apiKey, int $timeoutSeconds): AIResponse
    {
        $started = microtime(true);
        $ch = curl_init('https://api.openai.com/v1/chat/completions');
        $curlOptions = [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => max(10, $timeoutSeconds),
            CURLOPT_POST => true,
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/json',
                'Authorization: Bearer ' . $apiKey,
            ],
            CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
        ];

        $caFile = dirname(__DIR__, 4) . '/storage/certs/cacert.pem';
        if (is_file($caFile)) {
            $curlOptions[CURLOPT_CAINFO] = $caFile;
        }

        curl_setopt_array($ch, $curlOptions);
        $body = curl_exec($ch);
        $error = curl_error($ch);
        $status = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        curl_close($ch);

        $durationMs = (int) round((microtime(true) - $started) * 1000);
        $model = (string) ($payload['model'] ?? '');

        if ($body === false || $status < 200 || $status >= 300) {
            $message = $this->formatApiError($status, $error, (string) $body);
            app_log('error', 'AI provider OpenAI error', ['status' => $status, 'error' => $message, 'body' => substr((string) $body, 0, 500)]);
            return new AIResponse(false, '', [], $this->name(), $model, $durationMs, $this->estimateTokens(json_encode($payload) . (string) $body), 0.0, $message, (string) $body);
        }

        $json = json_decode((string) $body, true);
        $content = (string) ($json['choices'][0]['message']['content'] ?? '');
        $tokens = (int) ($json['usage']['total_tokens'] ?? $this->estimateTokens(json_encode($payload) . $content));

        return new AIResponse(
            true,
            $content,
            [],
            $this->name(),
            (string) ($json['model'] ?? $model),
            $durationMs,
            $tokens,
            $this->estimateCost($model, $tokens),
            null,
            (string) $body
        );
    }

    private function formatApiError(int $status, string $curlError, string $body): string
    {
        if ($curlError) {
            return $curlError;
        }

        $json = json_decode($body, true);
        $message = $json['error']['message'] ?? '';
        $code = $json['error']['code'] ?? '';

        if ($code === 'insufficient_quota') {
            return 'OpenAI sem cota/credito disponivel. Verifique billing, saldo e limites do projeto na plataforma OpenAI.';
        }

        if ($status === 429) {
            return $message ?: 'OpenAI limitou a requisicao. Verifique cota, billing ou tente novamente em alguns minutos.';
        }

        return $message ?: ('OpenAI HTTP ' . $status);
    }

    private function estimateTokens(string $text): int
    {
        return max(1, (int) ceil(strlen($text) / 4));
    }

    private function estimateCost(string $model, int $tokens): float
    {
        if (stripos($model, 'gpt-4o-mini') !== false) {
            return round(($tokens / 1000000) * 0.3, 6);
        }
        return 0.0;
    }
}
