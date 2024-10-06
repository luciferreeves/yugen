from django.shortcuts import redirect, render

from read.utils import get_chapter_pages, get_manga_data

# Create your views here.
def index(request):
    return redirect("home:index")

def read(request, manga_id, chapter_id):
    manga = get_manga_data(manga_id)
    
    pages = get_chapter_pages(chapter_id)
    
    chapters = manga["chapters"]
    current_chapter_index = next((i for i, chapter in enumerate(chapters) if chapter["id"] == chapter_id), None)
    next_chapter = chapters[current_chapter_index + 1] if current_chapter_index is not None and current_chapter_index + 1 < len(chapters) else None
    prev_chapter = chapters[current_chapter_index - 1] if current_chapter_index is not None and current_chapter_index - 1 >= 0 else None

    context = {
        "pages": pages,
        "manga": manga,
        "chapter_id": chapter_id,
        "next_chapter": next_chapter,
        "prev_chapter": prev_chapter,
    }

    return render(request, "read/read.html", context)


