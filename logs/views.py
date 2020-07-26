from django.contrib.auth.models import User
from django.db.models import Q
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
    Log page: render logs according to certain searching criteria.
    """
    query_set, search = Log.objects.all().order_by('-src_time'), dict()
    try:
        src_time_s = request.GET.get('src_time_s', '')
        src_time_e = request.GET.get('src_time_e', '')
        src_user = request.GET.get('src_user', '')
        src_addr = request.GET.get('src_addr', '')
        keyword = request.GET.get('keyword', '')
        if src_time_s != '':
            search['src_time_s'] = src_time_s
            query_set = query_set.filter(src_time__gte=src_time_s)
        if src_time_e != '':
            search['src_time_e'] = src_time_e
            query_set = query_set.filter(src_time__lte=src_time_e)
        if src_user != '':
            search['src_user'] = src_user
            query_set = query_set.filter(src_user=int(src_user))
        if src_addr != '':
            search['src_addr'] = src_addr
            query_set = query_set.filter(src_addr=src_addr)
        if keyword != '':
            search['keyword'] = keyword
            query_set = query_set.filter(Q(category__icontains=keyword) |
                                         Q(behavior__icontains=keyword) |
                                         Q(detailed__icontains=keyword))
    except ValueError:
        raise Http404()
    context = dict()
    context['page'], context['plim'], context['pcnt'], context['logs'] = utils.paginate(request, 50, query_set)
    context['logs'] = [log_to_dict(log) for log in context['logs']]
    context['search'] = search
    return render(request, 'logs.html', context)
