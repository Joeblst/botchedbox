from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('load_configs', views.load_configs, name="load_configs"),
]