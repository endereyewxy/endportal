from django.conf.urls import url
from django.urls import path

from blog import views

urlpatterns = [
    path('search/', views.search),
    url(r'^(?P<path>([-\w]*/)+)$', views.display),
]
