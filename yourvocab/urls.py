# -*- coding: utf-8 -*-
from django.contrib.auth.views import LogoutView
from django.urls import path, include

from yourvocab import views

urlpatterns = [
    path('', views.courses),
    path('course', views.course),
    path('course/<int:course_id>', views.course),
    path('course/<int:course_id>/lesson', views.lesson),
    path('course/<int:course_id>/lesson/<int:lesson_id>', views.lesson),
    path('course/<int:course_id>/lesson/<int:lesson_id>/check', views.check),
    path('signup', views.signup),
    path('account_activation_sent', views.account_activation_sent),
    path('activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/',
        views.activate, name='activate'),
    path('accounts/', include('django.contrib.auth.urls')),
    path("logout/", LogoutView.as_view(), name="logout"),
]

