from django.urls import path

from logs import views

urlpatterns = [
    path('', views.logs),
]
