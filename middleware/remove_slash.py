from django.http import HttpResponsePermanentRedirect

class RemoveSlashMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if '/admin' in request.path and not request.path.endswith('/'):
            return HttpResponsePermanentRedirect(request.path + '/')

        if request.path != '/' and request.path.endswith('/') and "/admin/" not in request.path:
            return HttpResponsePermanentRedirect(request.path[:-1])
        
        return self.get_response(request)