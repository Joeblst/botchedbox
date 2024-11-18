from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('testcases/', views.testcases, name="get_testcases"),
    path('testcases/load/', views.load_testcases, name="load_testcases"),
    path('testcases/<str:testcase_id>/delete/', views.delete_testcase, name='delete_testcase'),
    path('testcases/<str:testcase_id>/toggle/', views.toggle_testcase, name='toggle_testcase'),
    path('testcases/<str:testcase_id>/tests/', views.get_testcase_tests, name='get_testcase_tests'),
    path('benchmarks/start/', views.start_benchmark, name="start_benchmark"),
    path('benchmarks/', views.get_benchmarks, name="get_benchmarks"),
    path('benchmarks/<str:benchmark_id>/', views.get_benchmark, name='get_benchmark'),
    path('benchmarks/<str:benchmark_id>/delete', views.delete_benchmark, name='delete_benchmark'),
    path('benchmarks/<str:benchmark_id>/tests', views.get_tests, name="get_tests"),
    path('tests/<int:test_id>/', views.get_test, name='get_test'),
    path('tests/<int:test_id>/recalculate/', views.recalculate_score, name='recalculate_score'),
    path('response/<int:response_id>/validate/', views.manual_validation, name='manual_validation'),
    path('evaluation/problem_types/', views.get_evaluation_problem_types, name='get_evaluation_problem_types'),
    path('evaluation/problem_types/load/', views.load_evaluation_problem_types, name='load_evaluation_problem_types'),
    path('evaluation/models/', views.get_evaluation_models, name='get_evaluation_models'),
    path('evaluation/models/load/', views.load_evaluation_models, name='load_evaluation_models'),
    path('evaluation/summary/', views.get_evaluation_summary, name='get_evaluation_summary'),
    path('evaluation/summary/load/', views.load_evaluation_summary, name='load_evaluation_summary'),
]
