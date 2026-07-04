<?php

class SettingsRepository
{
    private PDO $db;
    private string $key;

    public function __construct(PDO $db)
    {
        global $config;
        $this->db = $db;
        $this->key = hash('sha256', (string) ($config['app_key'] ?: 'autohub-mvp'));
    }

    public function get(string $key, ?string $default = null): ?string
    {
        $stmt = $this->db->prepare('SELECT encrypted_value FROM integration_settings WHERE setting_key = ? LIMIT 1');
        $stmt->execute([$key]);
        $row = $stmt->fetch();
        if (!$row) {
            return $default;
        }
        return $this->decrypt((string) $row['encrypted_value']) ?? $default;
    }

    public function set(string $key, string $value): void
    {
        $encrypted = $this->encrypt($value);
        $sql = db_is_sqlite()
            ? 'INSERT INTO integration_settings (setting_key, encrypted_value, updated_at)
               VALUES (?, ?, NOW())
               ON CONFLICT(setting_key) DO UPDATE SET encrypted_value = excluded.encrypted_value, updated_at = NOW()'
            : 'INSERT INTO integration_settings (setting_key, encrypted_value, updated_at)
               VALUES (?, ?, NOW())
               ON DUPLICATE KEY UPDATE encrypted_value = VALUES(encrypted_value), updated_at = NOW()';
        $stmt = $this->db->prepare($sql);
        $stmt->execute([$key, $encrypted]);
    }

    public function masked(string $key): string
    {
        $value = $this->get($key, '');
        if (!$value) {
            return '';
        }
        return strlen($value) > 4 ? '****' . substr($value, -4) : '****';
    }

    private function encrypt(string $plain): string
    {
        $iv = random_bytes(16);
        $cipher = openssl_encrypt($plain, 'AES-256-CBC', hex2bin($this->key), OPENSSL_RAW_DATA, $iv);
        return base64_encode($iv . ($cipher ?: ''));
    }

    private function decrypt(string $payload): ?string
    {
        $raw = base64_decode($payload, true);
        if ($raw === false || strlen($raw) < 17) {
            return null;
        }
        $iv = substr($raw, 0, 16);
        $cipher = substr($raw, 16);
        $plain = openssl_decrypt($cipher, 'AES-256-CBC', hex2bin($this->key), OPENSSL_RAW_DATA, $iv);
        return $plain === false ? null : $plain;
    }
}
