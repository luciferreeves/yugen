# Generated by Django 5.1 on 2024-09-03 22:59

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("watch", "0017_alter_anime_trailer"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="anime",
            name="title",
        ),
        migrations.RemoveField(
            model_name="anime",
            name="trailer",
        ),
        migrations.AddField(
            model_name="animetitle",
            name="anime",
            field=models.OneToOneField(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="title",
                to="watch.anime",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="animetrailer",
            name="anime",
            field=models.OneToOneField(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="trailer",
                to="watch.anime",
            ),
            preserve_default=False,
        ),
    ]