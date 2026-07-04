ALTER TABLE offers ADD COLUMN correction_feedback TEXT NULL;
ALTER TABLE offers ADD COLUMN approved_at DATETIME NULL;
ALTER TABLE offers ADD COLUMN sent_at DATETIME NULL;
ALTER TABLE offers ADD COLUMN canceled_at DATETIME NULL;

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
