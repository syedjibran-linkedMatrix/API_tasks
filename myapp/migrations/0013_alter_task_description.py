# Generated by Django 5.1.2 on 2024-11-29 17:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0012_alter_project_title"),
    ]

    operations = [
        migrations.AlterField(
            model_name="task",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
    ]
