CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NULL
);

CREATE TABLE IF NOT EXISTS admins (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  phone TEXT NOT NULL UNIQUE,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NULL
);

CREATE TABLE IF NOT EXISTS buyers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  phone TEXT NOT NULL UNIQUE,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NULL
);

CREATE TABLE IF NOT EXISTS whatsapp_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NULL,
  sender_phone TEXT NOT NULL,
  sender_name TEXT NULL,
  message_type TEXT NULL,
  text_content TEXT NULL,
  raw_payload TEXT NULL,
  is_admin INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'received',
  processed_at TEXT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_whatsapp_sender_phone ON whatsapp_messages(sender_phone);
CREATE INDEX IF NOT EXISTS idx_whatsapp_created_at ON whatsapp_messages(created_at);

CREATE TABLE IF NOT EXISTS offers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  admin_id INTEGER NOT NULL,
  whatsapp_message_id INTEGER NULL,
  title TEXT NULL,
  description TEXT NULL,
  original_text TEXT NULL,
  final_text TEXT NULL,
  correction_feedback TEXT NULL,
  status TEXT NOT NULL DEFAULT 'recebida',
  sent_count INTEGER NOT NULL DEFAULT 0,
  error_message TEXT NULL,
  approved_at TEXT NULL,
  sent_at TEXT NULL,
  canceled_at TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_offers_status ON offers(status);
CREATE INDEX IF NOT EXISTS idx_offers_created_at ON offers(created_at);

CREATE TABLE IF NOT EXISTS offer_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  offer_id INTEGER NOT NULL,
  version_number INTEGER NOT NULL,
  title TEXT NULL,
  description TEXT NULL,
  final_text TEXT NULL,
  feedback TEXT NULL,
  source TEXT NOT NULL,
  admin_id INTEGER NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_offer_versions_offer_id ON offer_versions(offer_id);

CREATE TABLE IF NOT EXISTS offer_images (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  offer_id INTEGER NOT NULL,
  image_url TEXT NULL,
  image_base64 TEXT NULL,
  mimetype TEXT NULL,
  position INTEGER NOT NULL DEFAULT 1,
  decode_error TEXT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_offer_images_offer_id ON offer_images(offer_id);

CREATE TABLE IF NOT EXISTS send_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  offer_id INTEGER NOT NULL,
  buyer_id INTEGER NOT NULL,
  buyer_phone TEXT NOT NULL,
  image_id INTEGER NULL,
  message_type TEXT NOT NULL,
  caption TEXT NULL,
  success INTEGER NOT NULL DEFAULT 0,
  evolution_message_id TEXT NULL,
  error_message TEXT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_send_logs_offer_id ON send_logs(offer_id);
CREATE INDEX IF NOT EXISTS idx_send_logs_buyer_phone ON send_logs(buyer_phone);
CREATE INDEX IF NOT EXISTS idx_send_logs_created_at ON send_logs(created_at);

CREATE TABLE IF NOT EXISTS ai_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  offer_id INTEGER NOT NULL,
  user_id INTEGER NULL,
  origin TEXT NULL,
  function_name TEXT NULL,
  provider TEXT NULL,
  model TEXT NULL,
  duration_ms INTEGER NULL,
  tokens_estimated INTEGER NULL,
  cost_estimated REAL NULL,
  prompt TEXT NULL,
  response TEXT NULL,
  success INTEGER NOT NULL DEFAULT 0,
  error_message TEXT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_logs_offer_id ON ai_logs(offer_id);
CREATE INDEX IF NOT EXISTS idx_ai_logs_created_at ON ai_logs(created_at);

CREATE TABLE IF NOT EXISTS integration_settings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  setting_key TEXT NOT NULL UNIQUE,
  encrypted_value TEXT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NULL
);
