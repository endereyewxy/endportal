from django.contrib import auth

from wcmd.commands import WebCommand


class Login(WebCommand):
    """
    Authenticate an user by username and password, attach that user to the current session if success.
    """

    def __init__(self):
        super().__init__('login', 'Login current session.')
        self.add_pos_param('username', 'Username.')
        self.add_pos_param('password', 'Password.')

    def __call__(self, request, username, password):
        user = auth.authenticate(request, username=username, password=password)
        if user is None:
            raise WebCommand.Failed('Wrong username or password.')
        auth.login(request, user)


class Logout(WebCommand):
    """
    Remove an attached user from the current session.
    """

    def __init__(self):
        super().__init__('logout', 'Logout current session.')

    def __call__(self, request):
        if not request.user.is_authenticated:
            raise WebCommand.Failed('No user is attached to the current session, nothing to do.')
        auth.logout(request)


class WhoAmI(WebCommand):
    """
    Find out which user I am. Also will show email and permission information.
    """

    def __init__(self):
        super().__init__('whoami', 'Display the user attached to the current session.')

    def __call__(self, request):
        if not request.user.is_authenticated:
            raise WebCommand.Failed('No user is attached to the current session.')
        return '%s &lt;%s&gt;, %s superuser.' % \
               (request.user.username, request.user.email, 'is' if request.user.is_superuser else 'is not')


Login(), Logout(), WhoAmI()
