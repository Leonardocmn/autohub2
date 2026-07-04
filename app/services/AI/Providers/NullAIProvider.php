<?php

class NullAIProvider implements AIProviderInterface
{
    private string $provider;

    public function __construct(string $provider)
    {
        $this->provider = $provider;
    }

    public function name(): string
    {
        return $this->provider;
    }

    public function textCompletion(AIRequest $request): AIResponse
    {
        return new AIResponse(false, '', [], $this->provider, (string) $request->model, 0, 0, 0.0, 'Provedor de IA nao suportado ou nao configurado.');
    }

    public function visionCompletion(AIRequest $request): AIResponse
    {
        return $this->textCompletion($request);
    }

    public function testConnection(AIRequest $request): AIResponse
    {
        return $this->textCompletion($request);
    }
}
