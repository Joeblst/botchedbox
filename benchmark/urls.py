from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('testcases/', views.testcases, name="testcases"),
    path('testcases/load/', views.load_testcases, name="load_testcases"),
    path('benchmarks/start/', views.start_benchmark, name="start_benchmark"),
    path('benchmarks/', views.get_benchmarks, name="get_benchmark"),
    path('benchmarks/<str:benchmark_id>/', views.benchmark, name='benchmark'),
    path('benchmarks/<str:benchmark_id>/recalculate/', views.recalculate_benchmark_scores, name='recalculate_score'),
]