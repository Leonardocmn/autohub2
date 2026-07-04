<?php

interface AIProviderInterface
{
    public function name(): string;

    public function textCompletion(AIRequest $request): AIResponse;

    public function visionCompletion(AIRequest $request): AIResponse;

    public function testConnection(AIRequest $request): AIResponse;
}
