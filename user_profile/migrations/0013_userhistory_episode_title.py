# Generated by Django 5.1 on 2024-09-30 04:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("user_profile", "0012_userhistory_anime_cover_image_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="userhistory",
            name="episode_title",
            field=models.CharField(default="", max_length=256),
            preserve_default=False,
        ),
    ]
