from wcmd.commands import WebCommand


class Help(WebCommand):
    """
    Display help information.
    """

    def __init__(self):
        super().__init__('help', 'Display help information.')
        self.add_pos_param('command', 'Command to show help of.', default='')

    def __call__(self, request, command):
        # Determine whether we should show brief introductions of all commands, or just give a detailed explanation of
        # one command.
        if command == '':
            # The maximum length of all commands is calculated beforehand, so that we can align the descriptions.
            max_len = max([len(name) for name in WebCommand.commands])
            return '\n'.join(
                [name + ' ' * (max_len - len(name) + 1) + cmd.desc for name, cmd in WebCommand.commands.items()])
        else:
            if command not in WebCommand.commands:
                raise WebCommand.Failed('Command %s not found.' % command)
            command = WebCommand.commands[command]
            # Generate a usage string, including every single parameter, no matter positional or keyword.
            order = ' '.join([('&lt;%s&gt;' if param.default is None else '[%s]') % param.name
                              for param in command.order_params])
            named = ' '.join([('&lt;%s&gt;' if param.default is None else '[%s]') % ('--' + name + ' ' + name)
                              for name, param in command.named_params.items()])
            msg = command.name + ' ' + order + ' ' + named + ': ' + command.desc
            # Then append detailed explanations of very parameter. Similar to the previous all-command-introduction, we
            # calculate the maximum length of all parameters' name first.
            # This zero is required since some commands do no have parameters, and `max` cannot handle empty lists.
            max_len = max([0] +
                          [len(param.name) for param in command.order_params] +
                          [len(name) for name in command.named_params])

            def add_msg(msg, param):
                msg += '\n    ' + param.name + ' ' * (max_len - len(param.name) + 1) + param.desc
                if param.default is not None and len(param.default) > 0:
                    msg += '\n    ' + ' ' * (max_len + 1) + 'Default to be: ' + str(param.default)
                return msg

            for param in command.order_params:
                msg = add_msg(msg, param)
            for _, param in command.named_params:
                msg = add_msg(msg, param)
            return msg


Help()
