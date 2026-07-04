<?php

class EvolutionClient
{
    private SettingsRepository $settings;

    public function __construct(SettingsRepository $settings)
    {
        $this->settings = $settings;
    }

    public function isConfigured(): bool
    {
        return (bool) ($this->apiUrl() && $this->apiKey() && $this->instance());
    }

    public function testConnection(): array
    {
        if (!$this->isConfigured()) {
            return ['success' => false, 'error' => 'Evolution API nao configurada.'];
        }
        $res = $this->request('GET', '/instance/fetchInstances?instanceName=' . urlencode($this->instance()));
        if (!$res['success']) {
            return $res;
        }
        $instance = $this->findInstance($res['json']);
        if (!$instance) {
            return ['success' => false, 'error' => 'Instancia nao encontrada na Evolution API.'];
        }
        $status = $instance['connectionStatus'] ?? ($instance['status'] ?? ($instance['instance']['status'] ?? 'unknown'));
        return [
            'success' => in_array(strtolower((string) $status), ['open', 'connected', 'online'], true),
            'status' => $status,
            'error' => in_array(strtolower((string) $status), ['open', 'connected', 'online'], true) ? '' : 'Instancia encontrada, mas nao conectada.',
        ];
    }

    public function sendMedia(string $phone, string $media, string $caption = '', string $mimetype = 'image/jpeg'): array
    {
        if (!$this->isConfigured()) {
            return ['success' => false, 'error' => 'Evolution API nao configurada.'];
        }
        $number = normalize_phone($phone);
        if (!$number) {
            return ['success' => false, 'error' => 'Telefone invalido.'];
        }
        $payload = [
            'number' => $number,
            'mediatype' => 'image',
            'mimetype' => $mimetype ?: 'image/jpeg',
            'caption' => $caption,
            'media' => $media,
            'fileName' => 'autohub.' . $this->extensionFromMime($mimetype),
        ];
        $res = $this->request('POST', '/message/sendMedia/' . rawurlencode($this->instance()), $payload);
        if ($res['success']) {
            return ['success' => true, 'message_id' => $this->messageId($res['json']), 'response' => $res['json']];
        }

        $payload['number'] = $number . '@s.whatsapp.net';
        $retry = $this->request('POST', '/message/sendMedia/' . rawurlencode($this->instance()), $payload);
        if ($retry['success']) {
            return ['success' => true, 'message_id' => $this->messageId($retry['json']), 'response' => $retry['json']];
        }
        return $retry;
    }

    public function sendText(string $phone, string $text): array
    {
        if (!$this->isConfigured()) {
            return ['success' => false, 'error' => 'Evolution API nao configurada.'];
        }
        $number = normalize_phone($phone);
        if (!$number) {
            return ['success' => false, 'error' => 'Telefone invalido.'];
        }

        $payload = ['number' => $number, 'text' => $text];
        $res = $this->request('POST', '/message/sendText/' . rawurlencode($this->instance()), $payload);
        if ($res['success']) {
            return ['success' => true, 'message_id' => $this->messageId($res['json']), 'response' => $res['json']];
        }

        $payload['number'] = $number . '@s.whatsapp.net';
        $retry = $this->request('POST', '/message/sendText/' . rawurlencode($this->instance()), $payload);
        if ($retry['success']) {
            return ['success' => true, 'message_id' => $this->messageId($retry['json']), 'response' => $retry['json']];
        }
        return $retry;
    }

    public function getBase64FromMediaMessage(array $messageData): array
    {
        if (!$this->isConfigured()) {
            return ['success' => false, 'error' => 'Evolution API nao configurada.'];
        }
        $res = $this->request('POST', '/chat/getBase64FromMediaMessage/' . rawurlencode($this->instance()), [
            'message' => $messageData,
        ]);
        if (!$res['success']) {
            return $res;
        }
        return [
            'success' => true,
            'base64' => $res['json']['base64'] ?? '',
            'mimetype' => $res['json']['mimetype'] ?? 'image/jpeg',
            'filename' => $res['json']['filename'] ?? 'media.jpg',
        ];
    }

    private function request(string $method, string $path, ?array $payload = null): array
    {
        $url = $this->apiUrl() . $path;
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_TIMEOUT => 60,
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_HTTPHEADER => [
                'Content-Type: application/json',
                'apikey: ' . $this->apiKey(),
            ],
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_SSL_VERIFYHOST => 0,
        ]);
        if ($payload !== null) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
        }
        $body = curl_exec($ch);
        $error = curl_error($ch);
        $status = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        curl_close($ch);

        if ($body === false) {
            app_log('error', 'Evolution cURL error', ['error' => $error, 'url' => $url]);
            return ['success' => false, 'error' => $error ?: 'Erro cURL Evolution'];
        }
        $json = json_decode((string) $body, true);
        $ok = $status >= 200 && $status < 300;
        if (!$ok) {
            app_log('error', 'Evolution API error', ['status' => $status, 'body' => substr((string) $body, 0, 500)]);
        }
        return [
            'success' => $ok,
            'status' => $status,
            'json' => is_array($json) ? $json : [],
            'error' => $ok ? '' : 'Evolution API HTTP ' . $status . ': ' . substr((string) $body, 0, 200),
        ];
    }

    private function apiUrl(): string
    {
        return rtrim((string) $this->settings->get('EVOLUTION_API_URL', ''), '/');
    }

    private function apiKey(): string
    {
        return (string) $this->settings->get('EVOLUTION_API_KEY', '');
    }

    private function instance(): string
    {
        return (string) $this->settings->get('EVOLUTION_INSTANCE_NAME', '');
    }

    private function findInstance(array $data): ?array
    {
        $items = $data;
        if (isset($data['instances']) && is_array($data['instances'])) {
            $items = $data['instances'];
        }
        if (isset($data['data']) && is_array($data['data'])) {
            $items = $data['data'];
        }
        foreach ($items as $item) {
            if (!is_array($item)) {
                continue;
            }
            $name = $item['name'] ?? ($item['instanceName'] ?? ($item['instance']['instanceName'] ?? ''));
            if ($name === $this->instance()) {
                return $item;
            }
        }
        return null;
    }

    private function messageId(array $data): string
    {
        return $data['key']['id'] ?? ($data['message']['key']['id'] ?? ($data['messageId'] ?? ''));
    }

    private function extensionFromMime(string $mimetype): string
    {
        return match (strtolower($mimetype)) {
            'image/png' => 'png',
            'image/webp' => 'webp',
            default => 'jpg',
        };
    }
}
