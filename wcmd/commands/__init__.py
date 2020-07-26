class WebCommand:
    """
    The base class of all web commands.
    """
    commands = {}  # This is where all the commands supported are stored.

    class Parameter:
        def __init__(self, name, desc, type, default):
            self.name, self.desc, self.type, self.default = name, desc, type, default

    class Failed(BaseException):
        """
        Exception raised when a logic error takes place while executing a command.
        """

        def __init__(self, message):
            self.message = message

    # Note: A command will be registered only if it is instantiated, so simply extending this class is not enough.
    def __init__(self, name, desc, permission=None):
        """
        Initialize a command object and add it to supported commands.
        :param name: Name of the command.
        :param desc: Description (brief) of the command.
        :param permission: Permission required to execute this command. If there are no permissions required, use `None`.
        """
        self.name, self.desc, self.permission, self.pos_params, self.key_params = name, desc, permission, [], {}
        WebCommand.commands[name] = self

    def __call__(self, *args, **kwargs):
        """
        Execute the command.
        This method should be implemented by sub-classes.
        :param request: The HTTP request object.
        :return: The output of the command.
        :rtype: str
        """
        pass

    def add_pos_param(self, name, desc, type=str, default=None):
        """
        Add a positional parameter to the current command.
        :param name: Name.
        :param desc: Description.
        :param type: A function indicating how to transform the POST argument string into what we want.
        :param default: Default value. If not presented, this parameter is required.
        """
        self.pos_params.append(WebCommand.Parameter(name, desc, type, default))

    def add_key_param(self, name, desc, type=str, default=None):
        """
        Add a keyword parameter to the current command.
        :param name: Name.
        :param desc: Description.
        :param type: A function indicating how to transform the POST argument string into what we want.
        :param default: Default value. If not presented, this parameter is required.
        """
        self.key_params[name] = WebCommand.Parameter(name, desc, type, default)


# We have to import it here to avoid circular imports
from wcmd.commands import misc, user
