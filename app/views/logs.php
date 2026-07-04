<?php ob_start(); ?>
<div class="card">
  <h2>Logs de envio</h2>
  <p>Cada linha representa uma tentativa de enviar uma imagem para um comprador.</p>
</div>
<table class="table">
  <thead><tr><th>Data</th><th>Oferta</th><th>Comprador</th><th>Telefone</th><th>Status</th><th>Erro</th></tr></thead>
  <tbody>
  <?php foreach ($logs as $log): ?>
    <tr>
      <td><?= h($log['created_at']) ?></td>
      <td>#<?= (int) $log['offer_id'] ?></td>
      <td><?= h($log['buyer_name'] ?? '') ?></td>
      <td><?= h($log['buyer_phone']) ?></td>
      <td><span class="badge <?= $log['success'] ? 'ok' : 'err' ?>"><?= $log['success'] ? 'Enviado' : 'Erro' ?></span></td>
      <td><?= h($log['error_message']) ?></td>
    </tr>
  <?php endforeach; ?>
  </tbody>
</table>

<div class="card">
  <h2>Logs do AIService</h2>
  <p>Chamadas de inteligencia artificial feitas pelo backend.</p>
</div>
<table class="table">
  <thead><tr><th>Data</th><th>Funcao</th><th>Provedor</th><th>Modelo</th><th>Tempo</th><th>Tokens</th><th>Custo</th><th>Status</th><th>Erro</th></tr></thead>
  <tbody>
  <?php foreach ($aiLogs as $log): ?>
    <tr>
      <td><?= h($log['created_at']) ?></td>
      <td><?= h($log['function_name'] ?? '') ?></td>
      <td><?= h($log['provider'] ?? '') ?></td>
      <td><?= h($log['model'] ?? '') ?></td>
      <td><?= h((string) ($log['duration_ms'] ?? 0)) ?> ms</td>
      <td><?= h((string) ($log['tokens_estimated'] ?? 0)) ?></td>
      <td><?= h((string) ($log['cost_estimated'] ?? 0)) ?></td>
      <td><span class="badge <?= $log['success'] ? 'ok' : 'err' ?>"><?= $log['success'] ? 'Sucesso' : 'Erro' ?></span></td>
      <td><?= h($log['error_message'] ?? '') ?></td>
    </tr>
  <?php endforeach; ?>
  </tbody>
</table>
<?php $content = ob_get_clean(); require __DIR__ . '/layout.php'; ?>
