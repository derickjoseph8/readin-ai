-- Migration: Add Two-Factor Authentication columns to users table
-- Run this on the production database after deploying the new code

-- Add TOTP columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(32);
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_backup_codes TEXT DEFAULT '[]';

-- For SQLite (which doesn't support IF NOT EXISTS in ALTER TABLE):
-- Run these commands manually if the above fail:
--
-- ALTER TABLE users ADD COLUMN totp_secret VARCHAR(32);
-- ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN DEFAULT 0;
-- ALTER TABLE users ADD COLUMN totp_backup_codes TEXT DEFAULT '[]';
