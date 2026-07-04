<?php

class AILogger
{
    private PDO $db;

    public function __construct(PDO $db)
    {
        $this->db = $db;
    }

    public function record(?int $offerId, AIRequest $request, AIResponse $response, array $context = []): void
    {
        $columns = $this->columns();
        $data = [
            'offer_id' => $offerId ?: 0,
            'user_id' => $context['user_id'] ?? null,
            'origin' => $context['origin'] ?? '',
            'function_name' => $request->task,
            'provider' => $response->provider,
            'model' => $response->model,
            'duration_ms' => $response->durationMs,
            'tokens_estimated' => $response->tokensEstimated,
            'cost_estimated' => $response->costEstimated,
            'prompt' => substr($request->userPrompt, 0, 3000),
            'response' => substr($response->raw ?: $response->content, 0, 3000),
            'success' => $response->success ? 1 : 0,
            'error_message' => $response->error ?: '',
            'created_at' => date('Y-m-d H:i:s'),
        ];

        $insert = [];
        foreach ($data as $column => $value) {
            if (isset($columns[$column])) {
                $insert[$column] = $value;
            }
        }

        $names = array_keys($insert);
        $placeholders = implode(', ', array_fill(0, count($names), '?'));
        $sql = 'INSERT INTO ai_logs (' . implode(', ', $names) . ') VALUES (' . $placeholders . ')';
        $stmt = $this->db->prepare($sql);
        $stmt->execute(array_values($insert));
    }

    private function columns(): array
    {
        static $cached = null;
        if ($cached !== null) {
            return $cached;
        }

        $cached = [];
        if (db_is_sqlite()) {
            $stmt = $this->db->query('PRAGMA table_info(ai_logs)');
            foreach ($stmt->fetchAll() as $row) {
                $cached[(string) $row['name']] = true;
            }
            return $cached;
        }

        $stmt = $this->db->query('SHOW COLUMNS FROM ai_logs');
        foreach ($stmt->fetchAll() as $row) {
            $cached[(string) $row['Field']] = true;
        }
        return $cached;
    }
}
