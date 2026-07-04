<?php

class AIRequest
{
    public string $task;
    public string $systemPrompt;
    public string $userPrompt;
    public ?string $model;
    public float $temperature;
    public int $maxTokens;
    public int $timeoutSeconds;
    public int $maxRetries;
    public array $metadata;

    public function __construct(
        string $task,
        string $systemPrompt,
        string $userPrompt,
        ?string $model,
        float $temperature,
        int $maxTokens,
        int $timeoutSeconds,
        int $maxRetries,
        array $metadata = []
    ) {
        $this->task = $task;
        $this->systemPrompt = $systemPrompt;
        $this->userPrompt = $userPrompt;
        $this->model = $model;
        $this->temperature = $temperature;
        $this->maxTokens = $maxTokens;
        $this->timeoutSeconds = $timeoutSeconds;
        $this->maxRetries = $maxRetries;
        $this->metadata = $metadata;
    }
}
