import re

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import html
from django.views.decorators.http import require_POST, require_GET

from logs.models import Log
from wcmd.commands import WebCommand


def escape(s):
    """
    Escape normal text into html representation. The only difference between this function and `django.util.html.escape`
    is that this function also escapes whitespaces into `&nbsp;`s.
    :param s: String to be escaped.
    :return: Escaped string.
    :rtype: str
    """
    return html.escape(s).replace(' ', '&nbsp;')


@require_POST
def wcmd_exec(request):
    # The command may have consecutive whitespaces, so we cannot simply `.split(' ')`.
    text = re.split(r'\s+', request.POST.get('_', '').strip())
    # Some commands require special privileges, but technically everyone can access the web commandline page, so we log
    # everything.
    Log.new_log(request, 'wcmd', 'execute', ' '.join(text))
    # All possible failures are raised as WebCommand.Failed, so other exceptions will trigger 502 normally.
    try:
        if len(text) == 0 or text[0] not in WebCommand.commands:
            raise WebCommand.Failed('No such command.')
        command, args, kwargs = WebCommand.commands[text[0]], [], {}
        # Check permission.
        if command.permission is not None and \
                ((command.permission == 'superuser' and not request.user.is_superuser) or
                 not request.user.has_perm(command.permission)):
            return HttpResponse(status=403, content='Permission denied.')
        # Parse arguments.
        for i in range(1, len(text)):
            # Ignore tokens starting with '--'.
            # Instead of detecting the keyword of a parameter (i.e. --something), we detect the parameter value itself
            # and determine whether it is a positional parameter or a keyword parameter.
            if not text[i].startswith('--'):
                if text[i - 1].startswith('--'):
                    # This is a keyword parameter.
                    name = text[i - 1][2:]
                    if name not in command.key_params:
                        raise WebCommand.Failed('Unknown keyword parameter %s of value "%s". ' % (name, text[i]))
                    try:
                        kwargs[name] = command.key_params[name].type(text[i])
                    except ValueError:
                        raise WebCommand.Failed(
                            'Preprocessor of keyword parameter %s rejected value "%s".' % (name, text[i]))
                else:
                    # This is a positional parameter. The total count must not exceed.
                    if len(args) >= len(command.pos_params):
                        raise WebCommand.Failed('Too much arguments.')
                    param = command.pos_params[len(args)]
                    try:
                        args.append(param.type(text[i]))
                    except ValueError:
                        raise WebCommand.Failed(
                            'Preprocessor of positional parameter %s rejected value "%s".' % (param.name, text[i]))
        # If there are any positional parameters missing, use the default ones. If some parameter has no default value
        # (i.e. it is required), raise an error.
        for i in range(len(args), len(command.pos_params)):
            param = command.pos_params[i]
            if param.default is None:
                raise WebCommand.Failed('Positional parameter %s is required but not given.' % param.name)
            args.append(param.default)
        for name, param in command.key_params.items():
            if name not in kwargs:
                if param.default is None:
                    raise WebCommand.Failed('Keyword parameter %s is required but not given.' % name)
                kwargs[name] = param.default
        # Execute the command.
        resp = command(request, *args, **kwargs)
        # Use a single space as default if the command returns nothing. The space is needed because the front-end can
        # not correctly render empty strings.
        return HttpResponse(status=200, content=escape(resp or ' '))
    except WebCommand.Failed as e:
        return HttpResponse(status=400, content=escape(e.message))


@require_GET
def wcmd_wcui(request):
    return render(request, 'wcmd.html')
