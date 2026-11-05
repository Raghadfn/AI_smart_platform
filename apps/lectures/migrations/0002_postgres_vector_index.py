"""
هجرة فهرس pgvector HNSW - PostgreSQL فقط
HNSW vector index migration - PostgreSQL only
"""
from django.db import migrations


def create_vector_index(apps, schema_editor):
    """إنشاء فهرس HNSW للبحث الدلالي (PostgreSQL فقط)"""
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        CREATE INDEX IF NOT EXISTS lecture_chunk_embedding_idx
        ON lectures_lecturechunk
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def drop_vector_index(apps, schema_editor):
    """حذف فهرس HNSW"""
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "DROP INDEX IF EXISTS lecture_chunk_embedding_idx"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("lectures", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_vector_index, drop_vector_index),
    ]
