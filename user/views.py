from django.contrib import auth
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@require_POST
@csrf_exempt
def login(request):
    user = auth.authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
    if user is not None:
        auth.login(request, user)
        return redirect(request.POST.get('url', '/'))
    else:
        return HttpResponse(status=401)


@require_POST
@csrf_exempt
def logout(request):
    auth.logout(request)
    return redirect(request.POST.get('url', '/'))
