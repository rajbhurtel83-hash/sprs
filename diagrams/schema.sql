-- ============================================
-- Smart Property Rental System (SPRS)
-- PostgreSQL Database Schema
-- ============================================

-- Create database
-- CREATE DATABASE sprs_db;

-- ============================================
-- Users Table (extends Django's AbstractUser)
-- ============================================
CREATE TABLE IF NOT EXISTS users_user (
    id              BIGSERIAL PRIMARY KEY,
    password        VARCHAR(128) NOT NULL,
    last_login      TIMESTAMP WITH TIME ZONE,
    is_superuser    BOOLEAN NOT NULL DEFAULT FALSE,
    username        VARCHAR(150) NOT NULL UNIQUE,
    first_name      VARCHAR(150) NOT NULL DEFAULT '',
    last_name       VARCHAR(150) NOT NULL DEFAULT '',
    email           VARCHAR(254) NOT NULL DEFAULT '',
    is_staff        BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    role            VARCHAR(10) NOT NULL DEFAULT 'tenant'
                    CHECK (role IN ('tenant', 'owner', 'admin')),
    phone           VARCHAR(20) NOT NULL DEFAULT '',
    address         VARCHAR(255) NOT NULL DEFAULT '',
    profile_picture VARCHAR(100) DEFAULT NULL,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_role ON users_user(role);
CREATE INDEX idx_users_is_active ON users_user(is_active);
CREATE INDEX idx_users_date_joined ON users_user(date_joined);

-- ============================================
-- Properties Table
-- ============================================
CREATE TABLE IF NOT EXISTS properties_property (
    id              BIGSERIAL PRIMARY KEY,
    owner_id        BIGINT NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    title           VARCHAR(200) NOT NULL,
    property_type   VARCHAR(20) NOT NULL DEFAULT 'room'
                    CHECK (property_type IN ('room', 'flat', 'house', 'land', 'commercial')),
    description     TEXT NOT NULL,
    district        VARCHAR(100) NOT NULL,
    ward_number     VARCHAR(10) NOT NULL,
    address         VARCHAR(255) NOT NULL,
    price           DECIMAL(12, 2) NOT NULL,
    num_rooms       INTEGER NOT NULL DEFAULT 1 CHECK (num_rooms >= 0),
    status          VARCHAR(20) NOT NULL DEFAULT 'available'
                    CHECK (status IN ('available', 'rented', 'unavailable')),
    contact_phone   VARCHAR(20) NOT NULL DEFAULT '',
    contact_email   VARCHAR(254) NOT NULL DEFAULT '',
    is_approved     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_properties_owner ON properties_property(owner_id);
CREATE INDEX idx_properties_district ON properties_property(district);
CREATE INDEX idx_properties_type ON properties_property(property_type);
CREATE INDEX idx_properties_price ON properties_property(price);
CREATE INDEX idx_properties_status ON properties_property(status);
CREATE INDEX idx_properties_created ON properties_property(created_at);
CREATE INDEX idx_properties_approved ON properties_property(is_approved);

-- ============================================
-- Property Images Table
-- ============================================
CREATE TABLE IF NOT EXISTS properties_propertyimage (
    id              BIGSERIAL PRIMARY KEY,
    property_id     BIGINT NOT NULL REFERENCES properties_property(id) ON DELETE CASCADE,
    image           VARCHAR(100) NOT NULL,
    caption         VARCHAR(200) NOT NULL DEFAULT '',
    uploaded_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_images_property ON properties_propertyimage(property_id);

-- ============================================
-- Conversations Table
-- ============================================
CREATE TABLE IF NOT EXISTS messaging_conversation (
    id              BIGSERIAL PRIMARY KEY,
    property_id     BIGINT NOT NULL REFERENCES properties_property(id) ON DELETE CASCADE,
    tenant_id       BIGINT NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    owner_id        BIGINT NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(property_id, tenant_id)
);

CREATE INDEX idx_conv_property ON messaging_conversation(property_id);
CREATE INDEX idx_conv_tenant ON messaging_conversation(tenant_id);
CREATE INDEX idx_conv_owner ON messaging_conversation(owner_id);
CREATE INDEX idx_conv_updated ON messaging_conversation(updated_at);

-- ============================================
-- Messages Table
-- ============================================
CREATE TABLE IF NOT EXISTS messaging_message (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES messaging_conversation(id) ON DELETE CASCADE,
    sender_id       BIGINT NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_msg_conversation ON messaging_message(conversation_id);
CREATE INDEX idx_msg_sender ON messaging_message(sender_id);
CREATE INDEX idx_msg_is_read ON messaging_message(is_read);
CREATE INDEX idx_msg_created ON messaging_message(created_at);

-- ============================================
-- Django Required Tables (auto-created by migrate)
-- ============================================
-- auth_group
-- auth_group_permissions
-- auth_permission
-- django_admin_log
-- django_content_type
-- django_migrations
-- django_session
-- users_user_groups
-- users_user_user_permissions
