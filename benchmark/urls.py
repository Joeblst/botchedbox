from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('testcases', views.testcases, name="testcases"),
    path('load_testcases', views.load_testcases, name="load_testcases"),
]