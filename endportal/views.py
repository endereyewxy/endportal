from django.shortcuts import redirect, render


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
        return render(request, 'index.html')
