CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(190) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS admins (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  phone VARCHAR(30) NOT NULL UNIQUE,
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS buyers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  phone VARCHAR(30) NOT NULL UNIQUE,
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS whatsapp_messages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  event_id VARCHAR(120) NULL,
  sender_phone VARCHAR(30) NOT NULL,
  sender_name VARCHAR(120) NULL,
  message_type VARCHAR(30) NULL,
  text_content TEXT NULL,
  raw_payload LONGTEXT NULL,
  is_admin TINYINT(1) NOT NULL DEFAULT 0,
  status VARCHAR(30) NOT NULL DEFAULT 'received',
  processed_at DATETIME NULL,
  created_at DATETIME NOT NULL,
  INDEX idx_sender_phone (sender_phone),
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS offers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  admin_id INT NOT NULL,
  whatsapp_message_id INT NULL,
  title VARCHAR(190) NULL,
  description TEXT NULL,
  original_text TEXT NULL,
  final_text TEXT NULL,
  correction_feedback TEXT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'recebida',
  sent_count INT NOT NULL DEFAULT 0,
  error_message TEXT NULL,
  approved_at DATETIME NULL,
  sent_at DATETIME NULL,
  canceled_at DATETIME NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NULL,
  INDEX idx_status (status),
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS offer_versions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  offer_id INT NOT NULL,
  version_number INT NOT NULL,
  title VARCHAR(190) NULL,
  description TEXT NULL,
  final_text TEXT NULL,
  feedback TEXT NULL,
  source VARCHAR(60) NOT NULL,
  admin_id INT NULL,
  created_at DATETIME NOT NULL,
  INDEX idx_offer_id (offer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS offer_images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  offer_id INT NOT NULL,
  image_url TEXT NULL,
  image_base64 LONGTEXT NULL,
  mimetype VARCHAR(120) NULL,
  position INT NOT NULL DEFAULT 1,
  decode_error TEXT NULL,
  created_at DATETIME NOT NULL,
  INDEX idx_offer_id (offer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS send_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  offer_id INT NOT NULL,
  buyer_id INT NOT NULL,
  buyer_phone VARCHAR(30) NOT NULL,
  image_id INT NULL,
  message_type VARCHAR(30) NOT NULL,
  caption TEXT NULL,
  success TINYINT(1) NOT NULL DEFAULT 0,
  evolution_message_id VARCHAR(190) NULL,
  error_message TEXT NULL,
  created_at DATETIME NOT NULL,
  INDEX idx_offer_id (offer_id),
  INDEX idx_buyer_phone (buyer_phone),
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  offer_id INT NOT NULL,
  user_id INT NULL,
  origin VARCHAR(120) NULL,
  function_name VARCHAR(120) NULL,
  provider VARCHAR(60) NULL,
  model VARCHAR(120) NULL,
  duration_ms INT NULL,
  tokens_estimated INT NULL,
  cost_estimated DECIMAL(12,6) NULL,
  prompt LONGTEXT NULL,
  response LONGTEXT NULL,
  success TINYINT(1) NOT NULL DEFAULT 0,
  error_message TEXT NULL,
  created_at DATETIME NOT NULL,
  INDEX idx_offer_id (offer_id),
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS integration_settings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  setting_key VARCHAR(120) NOT NULL UNIQUE,
  encrypted_value LONGTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
