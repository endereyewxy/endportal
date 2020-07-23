from django.contrib.auth.models import User
from django.forms import model_to_dict
from django.http import Http404
from django.shortcuts import render

from endportal import utils
from logs.models import Log


def log_to_dict(log):
    """
    Transforms a log object into a dictionary. Source username field will be added.
    :param log: Log object.
    :return: Dictionary form of the given log.
    :rtype dict
    """
    log = model_to_dict(log)
    log['src_name'] = User.objects.get(id=log['src_user']) if log['src_user'] != 0 else '未登录用户'
    return log


def logs(request):
    """
    Log page: renders logs according to certain searching criteria.
    """
    # TODO more searching criteria.
    query_set = Log.objects.all().order_by('-src_time')
    try:
        if 'src_user' in request.GET:
            query_set = query_set.filter(src_user=int(request.GET.get('src_user')))
        if 'category' in request.GET:
            query_set = query_set.filter(category=request.GET.get('category'))
    except ValueError:
        raise Http404()
    context = dict()
    context['page'], context['plim'], context['pcnt'], context['logs'] = utils.paginate(request, 50, query_set)
    context['logs'] = [log_to_dict(log) for log in context['logs']]
    return render(request, 'logs.html', context)
