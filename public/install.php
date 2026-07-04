<?php

declare(strict_types=1);

$basePath = require __DIR__ . '/autohub_path.php';
$config = require $basePath . '/app/config.php';
require_once $basePath . '/app/helpers.php';
require_once $basePath . '/app/db.php';
require_once $basePath . '/app/logger.php';

$done = false;
$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        $schemaFile = db_is_sqlite() ? '/database/schema_sqlite.sql' : '/database/schema.sql';
        $schema = file_get_contents($basePath . $schemaFile);
        if (!$schema) {
            throw new RuntimeException('schema.sql nao encontrado.');
        }
        foreach (preg_split('/;\s*(\r?\n|$)/', $schema) as $statement) {
            $statement = trim($statement);
            if ($statement !== '') {
                db()->exec($statement);
            }
        }

        $name = post_value('name');
        $email = post_value('email');
        $password = post_value('password');
        if (!$name || !$email || strlen($password) < 8) {
            throw new RuntimeException('Informe nome, e-mail e senha com pelo menos 8 caracteres.');
        }

        $sql = db_is_sqlite()
            ? 'INSERT INTO users (name, email, password_hash, created_at)
               VALUES (?, ?, ?, NOW())
               ON CONFLICT(email) DO UPDATE SET name = excluded.name, password_hash = excluded.password_hash, updated_at = NOW()'
            : 'INSERT INTO users (name, email, password_hash, created_at)
               VALUES (?, ?, ?, NOW())
               ON DUPLICATE KEY UPDATE name = VALUES(name), password_hash = VALUES(password_hash), updated_at = NOW()';
        $stmt = db()->prepare($sql);
        $stmt->execute([$name, $email, password_hash($password, PASSWORD_DEFAULT)]);
        $done = true;
    } catch (Throwable $e) {
        $error = $e->getMessage();
    }
}
?>
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Instalar AutoHub MVP</title>
  <link rel="stylesheet" href="/assets/style.css">
</head>
<body class="auth-body">
  <main class="auth-card">
    <h1>Instalar AutoHub MVP</h1>
    <p>Crie as tabelas e o primeiro usuario de acesso.</p>
    <?php if ($done): ?>
      <div class="alert success">Instalacao concluida. Apague o arquivo <strong>public/install.php</strong> e acesse <a href="/login">/login</a>.</div>
    <?php else: ?>
      <?php if ($error): ?><div class="alert danger"><?= h($error) ?></div><?php endif; ?>
      <form method="post">
        <label>Nome<input name="name" required></label>
        <label>E-mail<input name="email" type="email" required></label>
        <label>Senha<input name="password" type="password" minlength="8" required></label>
        <button type="submit">Instalar</button>
      </form>
    <?php endif; ?>
  </main>
</body>
</html>
