from django.urls import path

from wcmd import views

urlpatterns = [
    path('exec/', views.wcmd_exec, name='wcmd-exec'),
    path('wcui/', views.wcmd_wcui, name='wcmd-wcui'),
]