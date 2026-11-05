-- ============================================
-- تهيئة قاعدة البيانات - تفعيل الامتدادات
-- Database initialization - enable extensions
-- ============================================

-- امتداد pgvector للبحث الدلالي (RAG)
CREATE EXTENSION IF NOT EXISTS vector;

-- امتداد البحث النصي الضبابي للعربية
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- امتداد البحث النصي الكامل
CREATE EXTENSION IF NOT EXISTS unaccent;
