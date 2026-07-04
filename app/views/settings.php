<?php ob_start(); ?>
<div class="grid">
  <section class="card">
    <h2>Evolution API</h2>
    <form method="post">
      <input type="hidden" name="_csrf" value="<?= h(csrf_token()) ?>">
      <input type="hidden" name="action" value="save_evolution">
      <label>URL da Evolution no VPS dedicado
        <input name="evolution_api_url" placeholder="https://143.95.217.12" value="<?= h($evolutionUrl) ?>">
      </label>
      <label>Instance name
        <input name="evolution_instance_name" value="<?= h($evolutionInstance) ?>">
      </label>
      <label>API Key
        <input name="evolution_api_key" type="password" placeholder="<?= h($evolutionKeyMasked ?: 'Informe a chave') ?>">
      </label>
      <button type="submit">Salvar Evolution</button>
    </form>
    <form method="post" style="margin-top:12px">
      <input type="hidden" name="_csrf" value="<?= h(csrf_token()) ?>">
      <input type="hidden" name="action" value="test_evolution">
      <button class="secondary" type="submit">Testar Evolution</button>
    </form>
  </section>

  <section class="card">
    <h2>AIService</h2>
    <form method="post">
      <input type="hidden" name="_csrf" value="<?= h(csrf_token()) ?>">
      <input type="hidden" name="action" value="save_ai">
      <label>Provedor padrao
        <select name="ai_default_provider">
          <option value="openai" <?= $aiDefaultProvider === 'openai' ? 'selected' : '' ?>>OpenAI</option>
        </select>
      </label>
      <label>Modelo
        <input name="ai_model" value="<?= h($aiModel) ?>">
      </label>
      <label>API Key
        <input name="ai_api_key" type="password" placeholder="<?= h($aiKeyMasked ?: 'Informe a chave') ?>">
      </label>
      <label>Temperatura
        <input name="ai_temperature" type="number" step="0.1" min="0" max="2" value="<?= h($aiTemperature) ?>">
      </label>
      <label>Limite de tokens
        <input name="ai_max_tokens" type="number" min="100" max="8000" value="<?= h($aiMaxTokens) ?>">
      </label>
      <label>Timeout em segundos
        <input name="ai_timeout_seconds" type="number" min="10" max="180" value="<?= h($aiTimeoutSeconds) ?>">
      </label>
      <label>Maximo de tentativas
        <input name="ai_max_retries" type="number" min="1" max="5" value="<?= h($aiMaxRetries) ?>">
      </label>
      <button type="submit">Salvar AIService</button>
    </form>
    <form method="post" style="margin-top:12px">
      <input type="hidden" name="_csrf" value="<?= h(csrf_token()) ?>">
      <input type="hidden" name="action" value="test_ai">
      <button class="secondary" type="submit">Testar AIService</button>
    </form>
  </section>
</div>

<section class="card">
  <h2>Webhook para configurar na Evolution</h2>
  <p>Use esta URL no servidor Evolution do VPS dedicado:</p>
  <input readonly value="<?= h($webhookUrl) ?>" onclick="this.select()">
</section>
<?php $content = ob_get_clean(); require __DIR__ . '/layout.php'; ?>
