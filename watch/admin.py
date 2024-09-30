# from django.contrib import admin
# from django.db import transaction

# Register your models here.
# from .models import Anime, AnimeGenre, AnimeStudio, AnimeTitle, AnimeTrailer, AnimeSeason, AnimeEpisode

# admin.site.register(AnimeGenre)
# admin.site.register(AnimeStudio)
# admin.site.register(AnimeTitle)
# admin.site.register(AnimeTrailer)
# admin.site.register(AnimeSeason)
# admin.site.register(AnimeEpisode)

# class AnimeTitleInline(admin.StackedInline):
#     model = AnimeTitle

# class AnimeTrailerInline(admin.StackedInline):
#     model = AnimeTrailer

# @admin.register(Anime)
# class AnimeAdmin(admin.ModelAdmin):
#     inlines = [AnimeTitleInline, AnimeTrailerInline]
#     list_display = ('id', 'get_title', 'status', 'totalEpisodes', 'currentEpisode')
#     search_fields = ('id', 'title__english', 'title__romaji')

#     def get_title(self, obj):
#         return str(obj.title) if hasattr(obj, 'title') else ''
#     get_title.short_description = 'Title'

#     @admin.action(description="Delete selected anime (including title and trailer)")
#     def delete_with_related(self, request, queryset):
#         queryset.delete()

#     actions = [delete_with_related]

