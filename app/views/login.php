<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Login - AutoHub MVP</title>
  <link rel="stylesheet" href="/assets/style.css">
</head>
<body class="auth-body">
  <main class="auth-card">
    <h1>AutoHub MVP</h1>
    <p>Acesse o painel administrativo.</p>
    <?php if (!empty($error)): ?><div class="alert danger"><?= h($error) ?></div><?php endif; ?>
    <form method="post" action="/login">
      <input type="hidden" name="_csrf" value="<?= h(csrf_token()) ?>">
      <label>E-mail<input name="email" type="email" required autofocus></label>
      <label>Senha<input name="password" type="password" required></label>
      <button type="submit">Entrar</button>
    </form>
  </main>
</body>
</html>

