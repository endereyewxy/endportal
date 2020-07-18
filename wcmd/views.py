from django.contrib import auth
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET


class WebCommand:
    commands = {}

    def __init__(self, function):
        self.parameters, self.description, self.function = {}, '', function

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)

    @staticmethod
    def command(name, description):
        def wrapper(w_cmd):
            if not isinstance(w_cmd, WebCommand):
                w_cmd = WebCommand(w_cmd)
            w_cmd.description = description
            WebCommand.commands[name] = w_cmd
            return w_cmd

        return wrapper


class WebCommandParameter:
    def __init__(self, description, transformer, required, default):
        self.description, self.transformer, self.required, self.default = description, transformer, required, default

    @staticmethod
    def parameter(name, description, transformer=str, required=True, default=None):
        def wrapper(w_cmd):
            if not isinstance(w_cmd, WebCommand):
                w_cmd = WebCommand(w_cmd)
            w_cmd.parameters[name] = WebCommandParameter(description, transformer, required, default)
            return w_cmd

        return wrapper


@WebCommand.command('login', 'Login current session.')
@WebCommandParameter.parameter('username', 'Username')
@WebCommandParameter.parameter('password', 'Password')
def do_login(request, username, password):
    user = auth.authenticate(request, username=username, password=password)
    if user is None:
        raise RuntimeError('Wrong username or password.')
    auth.login(request, user)
    msg = 'Ok, username: %s, email: %s.' % (user.username, user.email)
    if user.is_superuser:
        msg += '\nYou are a superuser.'
    return msg


@WebCommand.command('logout', 'Logout current session.')
def do_logout(request):
    if not request.user.is_authenticated:
        return 'No user is attached to current session yet.'
    else:
        auth.logout(request)
        return 'Ok.'


@WebCommand.command('user-status', 'Check current sessions\'s user status.')
def do_user_status(request):
    user = request.user
    if user.is_authenticated:
        return 'Username: %s, email: %s.' % (user.username, user.email)
    else:
        return 'No user is attached to this session.'


@WebCommand.command('help', 'Display help information.')
@WebCommandParameter.parameter('command', 'The command of help information to display.', required=False)
def do_help(request, command):
    if command is None:
        return '\n'.join([name + ': ' + cmd.description for name, cmd in WebCommand.commands.items()])
    if command not in WebCommand.commands:
        return HttpResponse(status=400, content='Command %s not found.' % command)
    cmd = WebCommand.commands[command]
    return command + ': ' + cmd.description + '\nParameters:\n' + '\n'.join(
        ['&nbsp;&nbsp;&nbsp;&nbsp;' + name + ': ' + param.description for name, param in cmd.parameters.items()])


@require_POST
@csrf_exempt
def wcmd_exec(request):
    command = request.POST.get('__command__')
    if command not in WebCommand.commands:
        return HttpResponse(status=400, content='Command %s not found.' % command)
    command, kwargs = WebCommand.commands[command], {}
    # The arguments presented by the user must match exactly the same as the command wants. No extra argument is
    # allowed, and not missing either (except for those marked not required).
    for key, val in request.POST.items():
        # Skip the `command` argument since it represents the command name.
        if key == '__command__':
            continue
        if key not in command.parameters:
            return HttpResponse(status=400, content='Unrecognized parameter %s.' % key)
        try:
            kwargs[key] = command.parameters[key].transformer(val)
        except ValueError or RuntimeError:
            return HttpResponse(status=400, content='Parameter %s is of wrong type and rejected.' % key)
    # Check if there are any missing arguments.
    for key, param in command.parameters.items():
        if key not in kwargs:
            if param.required:
                return HttpResponse(status=400, content='Parameter %s is required but not presented.' % key)
            kwargs[key] = param.default
    try:
        return HttpResponse(status=200, content=command(request, **kwargs))
    except RuntimeError as e:
        return HttpResponse(status=400, content=str(e))


@require_GET
def wcmd_wcui(request):
    return render(request, 'wcmd.html')
