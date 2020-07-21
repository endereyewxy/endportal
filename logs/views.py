from django.forms import model_to_dict
from django.shortcuts import render

from logs.models import Log


def logs(request):
    context = {'logs': [model_to_dict(log) for log in Log.objects.all()]}
    return render(request, 'logs.html', context)
