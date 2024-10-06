from django.shortcuts import redirect, render

from read.utils import decode_chapter_info, get_chapter_pages

# Create your views here.
def index(request):
    return redirect("home:index")

def read(request, manga_encoded_string):
    provider, chapter_id = decode_chapter_info(manga_encoded_string)
    print(f"Reading: {provider} - {chapter_id}")
    pages = get_chapter_pages(provider, chapter_id)

    context = {
        "pages": pages,
    }

    return render(request, "read/read.html", context)
