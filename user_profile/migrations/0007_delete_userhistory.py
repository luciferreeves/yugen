# Generated by Django 5.1 on 2024-09-03 20:09

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("user_profile", "0006_remove_userhistory_anime_remove_userhistory_episode"),
    ]

    operations = [
        migrations.DeleteModel(
            name="UserHistory",
        ),
    ]