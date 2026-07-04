<?php

class AIProviderFactory
{
    private SettingsRepository $settings;

    public function __construct(SettingsRepository $settings)
    {
        $this->settings = $settings;
    }

    public function make(string $provider): AIProviderInterface
    {
        $provider = strtolower(trim($provider));
        if ($provider === 'openai') {
            return new OpenAIProvider($this->settings);
        }
        return new NullAIProvider($provider ?: 'none');
    }
}
