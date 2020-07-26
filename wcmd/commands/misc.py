from threading import Thread
from time import sleep

from django.conf import settings
from django.contrib.staticfiles.management.commands import collectstatic
from django.core.management import CommandError

from wcmd.commands import WebCommand

# UWSGI is only provided in production environment. We try to import it, and do nothing if failed.
try:
    import uwsgi
except ModuleNotFoundError:
    pass


class Help(WebCommand):
    """
    Display help information. Will ignore unavailable commands.
    """

    def __init__(self):
        super().__init__('help', 'Display help information.')
        self.add_pos_param('command', 'Command to show help of.', default='')

    def __call__(self, request, command):
        # Determine whether we should show brief introductions of all commands, or just give a detailed explanation of
        # one command.
        if command == '':
            # The maximum length of all commands is calculated beforehand, so that we can align the descriptions.
            max_len = max([len(name) for name, cmd in WebCommand.commands.items() if cmd.available(request)])
            return '\n'.join([name + ' ' * (max_len - len(name) + 1) + cmd.desc
                              for name, cmd in WebCommand.commands.items() if cmd.available(request)])
        else:
            if command not in WebCommand.commands or not WebCommand.commands[command].available(request):
                raise WebCommand.Failed('Command %s not found.' % command)
            command = WebCommand.commands[command]
            # Generate a usage string, including every single parameter, no matter positional or keyword.
            order = ' '.join([('<%s>' if param.default is None else '[%s]') % param.name
                              for param in command.pos_params])
            named = ' '.join([('<%s>' if param.default is None else '[%s]') % ('--' + name + ' ' + name)
                              for name, param in command.key_params.items()])
            msg = command.name + ' ' + order + ' ' + named + ': ' + command.desc
            # Then append detailed explanations of very parameter. Similar to the previous all-command-introduction, we
            # calculate the maximum length of all parameters' name first.
            # This zero is required since some commands do no have parameters, and `max` cannot handle empty lists.
            max_len = max([0] +
                          [len(param.name) for param in command.pos_params] +
                          [len(name) for name in command.key_params])

            def add_msg(msg_, param):
                msg_ += '\n    ' + param.name + ' ' * (max_len - len(param.name) + 1) + param.desc
                if param.default is not None and param.default != '':
                    msg_ += '\n    ' + ' ' * (max_len + 1) + 'Default to be: ' + str(param.default)
                return msg_

            for param in command.pos_params:
                msg = add_msg(msg, param)
            for param in command.key_params.values():
                msg = add_msg(msg, param)
            return msg


class Restart(WebCommand):
    """
    Restart UWSGI server, requires superuser permission.
    """

    class RestartThread(Thread):
        def __init__(self, delay):
            super().__init__()
            self.delay = delay

        def run(self) -> None:
            sleep(self.delay / 1000)
            uwsgi.reload()

    def __init__(self):
        super().__init__('restart', 'Restart UWSGI server.', 'superuser')
        self.add_key_param('delay', 'Delay of restarting after executing this command, in milliseconds.', type=int,
                           default=5000)

    def __call__(self, request, delay):
        if settings.DEBUG:
            raise WebCommand.Failed('This is not production environment, no UWSGI available.')
        Restart.RestartThread(delay).start()
        return 'Restarting in %dms, see you later...' % delay


class CollectStatic(WebCommand):
    """
    Collect all static files into static root directory, requires superuser.
    """

    def __init__(self):
        super().__init__('collectstatic', 'Collect static files.', 'superuser')

    def __call__(self, request):
        try:
            # Enable verbosity to display more information, leave other options to default.
            result = collectstatic.Command().handle(interactive=False, verbosity=True, link=False, clear=False,
                                                    dry_run=False, ignore_patterns=[], use_default_ignore_patterns=True,
                                                    post_process=False)
            return result
        except CommandError as e:
            raise WebCommand.Failed(str(e))


Help(), Restart(), CollectStatic()
