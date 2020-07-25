from datetime import datetime
from platform import uname

from django.shortcuts import redirect, render

# UWSGI is only provided in production environment. We try to import it, and do nothing if failed.
try:
    import uwsgi
except ModuleNotFoundError:
    pass


def index(request):
    """
    Index page: decide which way to redirect (or what to display according to the login and permission status of the
    current session.
    If the current session has no attached user, or in other words, the user is anonymous, he will be redirected to the
     blog page, which is the only place he has access to.
    If the user is a superuser, an index page of all different apps is presented, for he has access to go anywhere.
    """
    if not request.user.is_authenticated:
        return redirect('blog-content', path='')
    if request.user.is_superuser:
        context = dict()
        try:
            context['uwsgi'] = {
                'proc_num': uwsgi.numproc,
                'workers': uwsgi.workers(),
                'started_on': datetime.fromtimestamp(uwsgi.started_on),
                'master_pid': uwsgi.masterpid(),
                'buffer_size': uwsgi.buffer_size
            }
        except NameError:
            pass
        platform = uname()
        context['system'] = {
            'system': platform.system + ' ' + platform.release,
            'version': platform.version,
            'machine': platform.node,
            'architecture': platform.machine,
            'processor': platform.processor
        }
        return render(request, 'index.html', context)
