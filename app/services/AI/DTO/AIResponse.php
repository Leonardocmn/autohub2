<?php

class AIResponse
{
    public bool $success;
    public string $content;
    public array $structuredData;
    public string $provider;
    public string $model;
    public int $durationMs;
    public int $tokensEstimated;
    public float $costEstimated;
    public ?string $error;
    public string $raw;

    public function __construct(
        bool $success,
        string $content = '',
        array $structuredData = [],
        string $provider = '',
        string $model = '',
        int $durationMs = 0,
        int $tokensEstimated = 0,
        float $costEstimated = 0.0,
        ?string $error = null,
        string $raw = ''
    ) {
        $this->success = $success;
        $this->content = $content;
        $this->structuredData = $structuredData;
        $this->provider = $provider;
        $this->model = $model;
        $this->durationMs = $durationMs;
        $this->tokensEstimated = $tokensEstimated;
        $this->costEstimated = $costEstimated;
        $this->error = $error;
        $this->raw = $raw;
    }

    public function toArray(): array
    {
        return [
            'success' => $this->success,
            'content' => $this->content,
            'structured_data' => $this->structuredData,
            'provider' => $this->provider,
            'model' => $this->model,
            'duration_ms' => $this->durationMs,
            'tokens_estimated' => $this->tokensEstimated,
            'cost_estimated' => $this->costEstimated,
            'error' => $this->error,
            'raw' => $this->raw,
        ];
    }
}
