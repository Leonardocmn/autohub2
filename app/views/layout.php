<?php
$user = auth_user();
$path = current_path();
$flash = flash();
?>
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title><?= h($title ?? 'AutoHub MVP') ?></title>
  <link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="brand">AutoHub MVP</div>
    <nav class="nav">
      <a class="<?= $path === '/' ? 'active' : '' ?>" href="/">Ofertas</a>
      <a class="<?= $path === '/admins' ? 'active' : '' ?>" href="/admins">Administradores</a>
      <a class="<?= $path === '/buyers' ? 'active' : '' ?>" href="/buyers">Compradores</a>
      <a class="<?= $path === '/settings' ? 'active' : '' ?>" href="/settings">Configurações</a>
      <a class="<?= $path === '/logs' ? 'active' : '' ?>" href="/logs">Logs de envio</a>
    </nav>
  </aside>
  <main class="main">
    <div class="topbar">
      <div>
        <h1><?= h($title ?? 'AutoHub MVP') ?></h1>
        <div class="muted">Fluxo simples: admin no WhatsApp → IA → compradores</div>
      </div>
      <div class="actions">
        <?php if ($user): ?><span class="muted"><?= h($user['name']) ?></span><a class="button secondary" href="/logout">Sair</a><?php endif; ?>
      </div>
    </div>
    <?php if ($flash): ?><div class="alert <?= h($flash['type']) ?>"><?= h($flash['message']) ?></div><?php endif; ?>
    <?= $content ?? '' ?>
  </main>
</div>
</body>
</html>

