from django.conf.urls import patterns, url, include
from django.contrib.auth.decorators import login_required
from django.utils.functional import curry
from django.views.defaults import *

from appv1 import views

urlpatterns = patterns('',
    url(r'^accounts/', include('allauth.urls')),
    url(r'^$', 'django.contrib.auth.views.login', {'template_name': 'account/login.html'}),
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'account/login.html'}),
    url(r'^environment/accounts/logout/$', 'django.contrib.auth.views.login',{'template_name': 'account/logout.html'}),
    #url(r'^session_load/$', views.session_load, name='session_load'),
    url(r'^dashboard/$', views.atlas_dashboard, name='dashboard'),
    url(r'^environment/(?P<environment>[a-z]{1,20}[\-\_]?[a-z]{1,20})/$', views.atlas_applications, name='applications'),
    url(r'^/login-error/$', views.login_error, name='login-error'),
)
