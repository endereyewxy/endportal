from django.contrib import auth
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@require_POST
def login(request):
    user = auth.authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
    if user is not None:
        auth.login(request, user)
        return HttpResponse(status=202)
    else:
        return HttpResponse(status=401)


@require_POST
@csrf_exempt
def logout(request):
    auth.logout(request)
    return HttpResponse(status=202)
