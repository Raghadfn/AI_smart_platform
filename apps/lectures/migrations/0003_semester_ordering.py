# Update lecture ordering for semester structure

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("lectures", "0002_postgres_vector_index"),
        ("curriculum", "0002_semester_structure"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="lecture",
            options={
                "ordering": ["subject__semester__year__order", "subject__order", "order"],
                "verbose_name": "محاضرة",
                "verbose_name_plural": "المحاضرات",
            },
        ),
    ]
