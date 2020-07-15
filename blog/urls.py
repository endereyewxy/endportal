from django.conf.urls import url

from blog import views

urlpatterns = [
    url(r'^indices/$', views.indices, name='blog-indices'),
    url(r'^publish/$', views.publish, name='blog-publish'),
    url(r'^(?P<path>([-\w]*/)*)$', views.content, name='blog-content'),
]
