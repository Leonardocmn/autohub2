<?php ob_start(); ?>
<div class="card">
  <h2>Ofertas recebidas</h2>
  <p>Mostra as mensagens aceitas de administradores e o resultado do envio aos compradores.</p>
</div>
<table class="table">
  <thead><tr><th>ID</th><th>Status</th><th>Título</th><th>Mensagem final</th><th>Envios</th><th>Data</th></tr></thead>
  <tbody>
  <?php foreach ($offers as $offer): ?>
    <tr>
      <td>#<?= (int) $offer['id'] ?></td>
      <td><span class="badge <?= $offer['status'] === 'sent' ? 'ok' : ($offer['status'] === 'error' ? 'err' : '') ?>"><?= h($offer['status']) ?></span></td>
      <td><?= h($offer['title'] ?: 'Sem título') ?></td>
      <td><?= nl2br(h(short_text((string) $offer['final_text']))) ?></td>
      <td><?= (int) $offer['sent_count'] ?></td>
      <td><?= h($offer['created_at']) ?></td>
    </tr>
  <?php endforeach; ?>
  </tbody>
</table>
<?php $content = ob_get_clean(); require __DIR__ . '/layout.php'; ?>
