<?php

class AITaskRouter
{
    private SettingsRepository $settings;

    public function __construct(SettingsRepository $settings)
    {
        $this->settings = $settings;
    }

    public function configFor(string $task): array
    {
        return [
            'provider' => $this->settings->get('AI_DEFAULT_PROVIDER', 'openai'),
            'model' => $this->settings->get('AI_MODEL', $this->settings->get('OPENAI_MODEL', 'gpt-4o-mini')),
            'temperature' => (float) $this->settings->get('AI_TEMPERATURE', '0.2'),
            'max_tokens' => (int) $this->settings->get('AI_MAX_TOKENS', '900'),
            'timeout_seconds' => (int) $this->settings->get('AI_TIMEOUT_SECONDS', '60'),
            'max_retries' => (int) $this->settings->get('AI_MAX_RETRIES', '1'),
        ];
    }
}
