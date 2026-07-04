<?php ob_start(); ?>
<div class="grid">
  <section class="card">
    <h2>Novo comprador</h2>
    <form method="post">
      <input type="hidden" name="_csrf" value="<?= h(csrf_token()) ?>">
      <input type="hidden" name="action" value="create">
      <label>Nome<input name="name" required></label>
      <label>Telefone com DDI<input name="phone" placeholder="5521999999999" required></label>
      <button type="submit">Salvar</button>
    </form>
  </section>
  <section class="card">
    <h2>Lista sem duplicidade</h2>
    <p>Todos os compradores ativos recebem todas as ofertas. Categorias nao sao usadas neste MVP.</p>
  </section>
</div>
<table class="table">
  <thead><tr><th>Nome</th><th>Telefone</th><th>Status</th><th></th></tr></thead>
  <tbody>
  <?php foreach ($buyers as $buyer): ?>
    <tr>
      <td><?= h($buyer['name']) ?></td>
      <td><?= h($buyer['phone']) ?></td>
      <td><span class="badge <?= $buyer['active'] ? 'ok' : '' ?>"><?= $buyer['active'] ? 'Ativo' : 'Inativo' ?></span></td>
      <td>
        <form method="post" class="actions">
          <input type="hidden" name="_csrf" value="<?= h(csrf_token()) ?>">
          <input type="hidden" name="action" value="toggle">
          <input type="hidden" name="id" value="<?= (int) $buyer['id'] ?>">
          <button class="secondary" type="submit"><?= $buyer['active'] ? 'Desativar' : 'Ativar' ?></button>
        </form>
      </td>
    </tr>
  <?php endforeach; ?>
  </tbody>
</table>
<?php $content = ob_get_clean(); require __DIR__ . '/layout.php'; ?>
