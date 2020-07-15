from django.conf.urls import url

from blog import views

urlpatterns = [
    url(r'^(?P<path>([-\w]*/)*)$', views.display)
]
