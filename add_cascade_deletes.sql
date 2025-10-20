-- Migration: Add CASCADE DELETE to all foreign keys referencing users table
-- This allows automatic deletion of all related records when deleting a user
-- Run this script with: psql $DATABASE_URL -f add_cascade_deletes.sql

BEGIN;

-- 1. user_rods table
-- Drop existing constraint and recreate with CASCADE
ALTER TABLE user_rods DROP CONSTRAINT IF EXISTS user_rods_user_id_fkey;
ALTER TABLE user_rods ADD CONSTRAINT user_rods_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE;

-- 2. user_settings table
ALTER TABLE user_settings DROP CONSTRAINT IF EXISTS user_settings_user_id_fkey;
ALTER TABLE user_settings ADD CONSTRAINT user_settings_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE;

-- 3. user_balances table
ALTER TABLE user_balances DROP CONSTRAINT IF EXISTS user_balances_user_id_fkey;
ALTER TABLE user_balances ADD CONSTRAINT user_balances_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE;

-- 4. positions table
ALTER TABLE positions DROP CONSTRAINT IF EXISTS positions_user_id_fkey;
ALTER TABLE positions ADD CONSTRAINT positions_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE;

-- 5. group_memberships table
ALTER TABLE group_memberships DROP CONSTRAINT IF EXISTS group_memberships_user_id_fkey;
ALTER TABLE group_memberships ADD CONSTRAINT group_memberships_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE;

-- 6. transactions table
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_user_id_fkey;
ALTER TABLE transactions ADD CONSTRAINT transactions_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE;

-- 7. onboarding_progress table
ALTER TABLE onboarding_progress DROP CONSTRAINT IF EXISTS onboarding_progress_user_id_fkey;
ALTER TABLE onboarding_progress ADD CONSTRAINT onboarding_progress_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE;

COMMIT;

-- Verification: Check all foreign keys now have CASCADE
SELECT
    tc.table_name,
    tc.constraint_name,
    rc.delete_rule
FROM information_schema.table_constraints tc
JOIN information_schema.referential_constraints rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
    AND rc.delete_rule = 'CASCADE'
    AND tc.constraint_name LIKE '%user_id_fkey'
ORDER BY tc.table_name;
