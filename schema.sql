-- UdharBand Database Schema
-- Run this in the Supabase SQL Editor to set up your database.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    email        TEXT PRIMARY KEY,
    display_name TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE groups (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name       TEXT NOT NULL,
    created_by TEXT NOT NULL REFERENCES users(email),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE group_members (
    group_id   UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_email TEXT NOT NULL REFERENCES users(email),
    added_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (group_id, user_email)
);

CREATE TABLE events (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id   UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    created_by TEXT NOT NULL REFERENCES users(email),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (group_id, name)
);

CREATE TABLE expenses (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id    UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    amount      NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    paid_by     TEXT NOT NULL REFERENCES users(email),
    created_by  TEXT NOT NULL REFERENCES users(email),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE expense_shares (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    expense_id   UUID NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
    user_email   TEXT NOT NULL REFERENCES users(email),
    share_amount NUMERIC(12, 2) NOT NULL CHECK (share_amount >= 0),
    UNIQUE (expense_id, user_email)
);

CREATE TABLE settlement_status (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id     UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    debtor_email TEXT NOT NULL REFERENCES users(email),
    creditor_email TEXT NOT NULL REFERENCES users(email),
    amount       NUMERIC(12, 2) NOT NULL,
    status       TEXT NOT NULL DEFAULT 'pending',
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (event_id, debtor_email, creditor_email)
);
