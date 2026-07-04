<?php

class AIService
{
    private AITaskRouter $router;
    private AIProviderFactory $providers;
    private AILogger $logger;

    public function __construct(AITaskRouter $router, AIProviderFactory $providers, AILogger $logger)
    {
        $this->router = $router;
        $this->providers = $providers;
        $this->logger = $logger;
    }

    public function analisarOferta(string $description, array $context = []): array
    {
        return $this->padronizarDescricao($description, $context);
    }

    public function padronizarDescricao(string $description, array $context = []): array
    {
        return $this->padronizarPrompt('padronizar_descricao', AIPromptRegistry::padronizarDescricao($description), $context);
    }

    public function corrigirAnuncio(string $previousMessage, string $feedback, array $context = []): array
    {
        return $this->padronizarPrompt('corrigir_anuncio', AIPromptRegistry::corrigirDescricao($previousMessage, $feedback), $context);
    }

    private function padronizarPrompt(string $task, string $prompt, array $context = []): array
    {
        $response = $this->runTextTask($task, $prompt, $context);
        if (!$response->success) {
            return ['success' => false, 'error' => $response->error, 'raw' => $response->raw];
        }

        $parsed = json_decode($response->content, true);
        if (!is_array($parsed)) {
            return ['success' => false, 'error' => 'Resposta da IA nao veio em JSON valido.', 'raw' => $response->content];
        }

        $title = AISanitizer::sensitive((string) ($parsed['title'] ?? 'NOVA OFERTA AUTOHUB'));
        $description = AISanitizer::sensitive((string) ($parsed['description'] ?? ''));
        $final = AISanitizer::sensitive((string) ($parsed['final_message'] ?? ''));
        if (!$this->hasVehicleDetails($final) && $description) {
            $final = $this->buildFinalMessage($title, $description);
        }
        return [
            'success' => true,
            'title' => $title,
            'description' => $description ?: $final,
            'final_message' => $final,
            'provider' => $response->provider,
            'model' => $response->model,
            'duration_ms' => $response->durationMs,
            'tokens_estimated' => $response->tokensEstimated,
            'cost_estimated' => $response->costEstimated,
            'raw' => $response->raw,
        ];
    }

    public function removerInformacoesSensiveis(string $text, array $context = []): array
    {
        return ['success' => true, 'text' => AISanitizer::sensitive($text)];
    }

    public function responderComprador(string $message, array $context = []): array
    {
        return $this->notImplemented('responderComprador');
    }

    public function gerarResumo(string $text, array $context = []): array
    {
        return $this->notImplemented('gerarResumo');
    }

    public function interpretarMensagem(string $message, array $context = []): array
    {
        return $this->notImplemented('interpretarMensagem');
    }

    public function detectarNegociacao(string $message, array $context = []): array
    {
        return $this->notImplemented('detectarNegociacao');
    }

    public function extrairDadosVeiculo(string $message, array $context = []): array
    {
        $response = $this->runTextTask('extrair_dados_veiculo', $message, $context);
        if (!$response->success) {
            return ['success' => false, 'error' => $response->error, 'raw' => $response->raw];
        }
        $parsed = json_decode($response->content, true);
        return ['success' => is_array($parsed), 'data' => is_array($parsed) ? $parsed : [], 'raw' => $response->content];
    }

    public function testConnection(array $context = []): array
    {
        $response = $this->runTextTask('teste_conexao', 'Teste: Honda Civic 2020 completo. Placa ABC1D23. Falar com Joao 11999999999. Retorne JSON com {"ok":true}.', $context);
        return ['success' => $response->success, 'error' => $response->error ?? '', 'provider' => $response->provider, 'model' => $response->model];
    }

    private function runTextTask(string $task, string $userPrompt, array $context = []): AIResponse
    {
        $config = $this->router->configFor($task);
        $request = new AIRequest(
            $task,
            AIPromptRegistry::systemFor($task),
            $userPrompt,
            (string) $config['model'],
            (float) $config['temperature'],
            (int) $config['max_tokens'],
            (int) $config['timeout_seconds'],
            (int) $config['max_retries'],
            $context
        );

        $provider = $this->providers->make((string) $config['provider']);
        $response = $task === 'teste_conexao'
            ? $provider->testConnection($request)
            : $provider->textCompletion($request);

        $this->logger->record(isset($context['offer_id']) ? (int) $context['offer_id'] : null, $request, $response, $context);
        return $response;
    }

    private function notImplemented(string $function): array
    {
        return ['success' => false, 'error' => $function . ' ainda nao implementado no MVP.'];
    }

    private function hasVehicleDetails(string $message): bool
    {
        return stripos($message, 'Veiculo:') !== false
            || stripos($message, 'Carro:') !== false
            || stripos($message, 'Ano:') !== false;
    }

    private function buildFinalMessage(string $title, string $description): string
    {
        return '*' . trim($title, "* \n\r\t") . "*\n\n" . trim($description) . "\n\nInteressados, chamar a AutoHub.";
    }
}
