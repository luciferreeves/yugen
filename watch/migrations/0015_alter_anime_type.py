# Generated by Django 5.1 on 2024-09-03 22:31

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("watch", "0014_alter_anime_rating"),
    ]

    operations = [
        migrations.AlterField(
            model_name="anime",
            name="type",
            field=models.CharField(max_length=255, null=True),
        ),
    ]