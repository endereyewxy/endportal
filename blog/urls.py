from django.conf.urls import url

from blog import views

urlpatterns = [
    url('^([-\\w]*/)*$', views.display)
]
