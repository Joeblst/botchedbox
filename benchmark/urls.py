from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('testcases/', views.testcases, name="get_testcases"),
    path('testcases/load/', views.load_testcases, name="load_testcases"),
    path('testcases/<str:testcase_id>/delete/', views.delete_testcase, name='delete_testcase'),
    path('benchmarks/start/', views.start_benchmark, name="start_benchmark"),
    path('benchmarks/', views.get_benchmarks, name="get_benchmarks"),
    path('benchmarks/<str:benchmark_id>/', views.get_benchmark, name='get_benchmark'),
    path('benchmarks/<str:benchmark_id>/delete', views.delete_benchmark, name='delete_benchmark'),
    path('benchmarks/<str:benchmark_id>/tests', views.get_tests, name="get_tests"),
    path('tests/<int:test_id>/', views.get_test, name='get_test'),
    path('tests/<int:test_id>/recalculate/', views.recalculate_score, name='recalculate_score'),
]
