import re
from watch.utils import get_anime_data

class GlobalMetaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def get_anime_title_description(self, anime_info, title_lang="english"):
        if "description" in anime_info:
            description = anime_info["description"]
            description = re.sub('<[^<]+?>', '', description)
        else:
            description = "Welcome to Yugen! Stream anime and read manga. Get the latest anime schedule and browse and add anime to your watchlist."

        if title_lang == "english" and "english" in anime_info["title"]:
            title = anime_info["title"]["english"]
        elif title_lang == "romaji" and "romaji" in anime_info["title"]:
            title = anime_info["title"]["romaji"]
        else:
            title = anime_info["title"]["native"]

        return title, description

    def __call__(self, request):
        request.meta = {
            "title": "Yugen — Stream Anime | Read Manga | Anime Schedule | Anime List",
            "description": "Welcome to Yugen! Stream anime and read manga. Get the latest anime schedule and browse and add anime to your watchlist.",
            "image": "https://anime.rize.moe/static/icons/Yugen.png",
            "url": "{}://{}{}".format(request.scheme, request.get_host(), request.path),
            "robots": "index, follow",
        }

        full_path = request.get_full_path()
        if '/search' in full_path:
            request.meta["title"] = "Search Anime | Yugen"
            request.meta["description"] = "Search for your favorite anime on Yugen. Stream and watch the latest anime episodes. Read manga and explore the latest anime schedule."

        if '/search?sort=%5B%22TRENDING_DESC%22%5D' in full_path or '/search?sort=[%22TRENDING_DESC%22]' in full_path:
            request.meta["title"] = "Trending Anime | Yugen"
            request.meta["description"] = "Discover the most popular anime on Yugen. Stream and watch the latest anime episodes. Read manga and explore the latest anime schedule."

        if '/schedule' in full_path:
            request.meta["title"] = "Anime Schedule | Yugen"
            request.meta["description"] = "Explore the latest anime schedule on Yugen. Stream and watch the latest anime episodes. Read manga and discover the most popular anime."

        if '/watchlist' in full_path:
            request.meta["title"] = "Watchlist | Yugen"
            request.meta["description"] = "Explore your watchlist on Yugen. Stream and watch the latest anime episodes. Read manga and discover the most popular anime."

        if '/profile' in full_path:
            request.meta["title"] = "Profile | Yugen"
            request.meta["description"] = "Explore your profile on Yugen. Stream and watch the latest anime episodes. Read manga and discover the most popular anime."
        
        if '/detail/' in full_path:
            requested_id = request.path.split("/")[2]
            anime_info = get_anime_data(requested_id)
            title, description = self.get_anime_title_description(anime_info)

            request.meta["title"] = f"{title} | Yugen"
            request.meta["description"] = description
            request.meta["image"] = anime_info["image"]

        if '/watch/' in full_path:
            paths_to_ignore = [
                '/watch/update_watch_history',
                '/watch/remove_anime_from_watchlist',
            ]

            if any(path in full_path for path in paths_to_ignore):
                response = self.get_response(request)
                return response

            requested_id = request.path.split("/")[2]
            episode = request.path.split("/")[3] if len(request.path.split("/")) > 3 else 1
            episode = int(episode)
            anime_info = get_anime_data(requested_id)

            if len(anime_info["episodes"] or []) < episode:
                episode = len(anime_info["episodes"])
            
            if episode <= 0:
                episode = 1
            title, description = self.get_anime_title_description(anime_info)

            request.meta["title"] = f"Watch {title} Episode {episode} | Yugen"
            request.meta["description"] = description
            request.meta["image"] = anime_info["image"]

        response = self.get_response(request)

        return response