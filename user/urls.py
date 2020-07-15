from django.urls import path

from user import views

urlpatterns = [
    path('login/', views.login, name='user-login'),
    path('logout/', views.logout, name='user-logout'),
]
