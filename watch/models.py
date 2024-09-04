from django.db import models
from django.utils import timezone
import datetime
class AnimeGenre(models.Model):
    genre_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class AnimeStudio(models.Model):
    studio_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name  

class AnimeTitle(models.Model):
    title_id = models.AutoField(primary_key=True)
    anime = models.OneToOneField('Anime', on_delete=models.CASCADE, related_name='title')
    english = models.CharField(max_length=255, blank=True, null=True)
    romaji = models.CharField(max_length=255, blank=True, null=True)
    native = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.english if self.english else self.romaji

class AnimeTrailer(models.Model):
    trailer_id = models.AutoField(primary_key=True)
    anime = models.OneToOneField('Anime', on_delete=models.CASCADE, related_name='trailer')
    id = models.CharField(max_length=255)
    site = models.CharField(max_length=255)
    thumbnail = models.URLField()

    def __str__(self):
        return self.id

class Anime(models.Model):
    anime_id = models.AutoField(primary_key=True)
    id = models.CharField(max_length=255, unique=True)
    malId = models.IntegerField(null=True)
    z_anime_id = models.CharField(max_length=255, null=True)
    description = models.TextField(null=True)
    image = models.URLField()
    cover = models.URLField()
    countryOfOrigin = models.CharField(max_length=255, null=True)
    popularity = models.IntegerField(null=True)
    color = models.CharField(max_length=255, null=True)
    releaseDate = models.IntegerField(null=True)
    totalEpisodes = models.IntegerField(null=True)
    currentEpisode = models.IntegerField(null=True)
    dub = models.IntegerField(default=0)
    sub = models.IntegerField(default=0)
    rating = models.IntegerField(null=True)
    duration = models.IntegerField(null=True)
    genres = models.ManyToManyField('AnimeGenre', blank=True)
    type = models.CharField(max_length=255, null=True)
    season = models.CharField(max_length=255, null=True)
    studios = models.ManyToManyField('AnimeStudio', blank=True)
    status = models.CharField(max_length=255)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title.english if self.title.english else self.title.romaji

    def needs_update(self):
        # Always update if the anime is ongoing and last updated was more than 1 day ago 
        if self.status == "Ongoing":
            return True
        
        if self.status == "Not yet aired":
            return True
        
        # Update if the current episode count doesn't match the total episodes for a completed anime
        if self.status == "Completed" and self.currentEpisode != self.totalEpisodes:
            return True
        
        if not self.z_anime_id or not self.description or not self.image or not self.cover:
            return True
        
        # Otherwise, no update is needed
        return False

    def delete(self, *args, **kwargs):
        # Delete the associated title
        if self.title:
            self.title.delete()
        
        # Delete the associated trailer
        if self.trailer:
            self.trailer.delete()
        
        # Call the "real" delete() method
        super().delete(*args, **kwargs)

class AnimeSeason(models.Model):
    season_id = models.AutoField(primary_key=True)
    id = models.CharField(max_length=255)
    anime = models.ForeignKey(Anime, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    poster = models.URLField()
    isCurrent = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title

class AnimeEpisode(models.Model):
    episode_id = models.AutoField(primary_key=True)
    anime = models.ForeignKey(Anime, on_delete=models.CASCADE)
    zEpisodeId = models.CharField(max_length=255, null=True)
    title = models.CharField(max_length=255)
    number = models.IntegerField()
    description = models.TextField()
    air_date = models.DateField()
    filler = models.BooleanField(default=False)
    image = models.URLField()

    def __str__(self):
        return f"{self.anime.title} - {self.number}. {self.title}"