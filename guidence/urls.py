from django.urls import path
from . import views
from .views import *

urlpatterns = [
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),
    path('', views.signin, name='sign-in'),
    path('sign-up/', views.signup, name='sign-up'),
    path('forgot-password/',views.forgotpassword,name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('admin_profile/',views.admin_profile,name='admin_profile'),
    path('user_profile/',views.user_profile,name='user_profile'),
    path('admin_patients/',views.admin_patients,name='admin_patients'),
    path('health_profile/',views.health_profile,name='health_profile'),
    path('add_symptom/',views.add_symptom,name='add_symptom'),
    path("add-symptom/<int:pk>/", views.add_symptom, name="update_symptom"),
    path("symptom-history/", views.user_symptom_history, name="user_symptom_history"),
    path("admin_symptom_history/", views.admin_symptom_history, name="admin_symptom_history"),
    path("delete-symptom/<int:pk>/", views.delete_symptom, name="delete_symptom"),
    path('admin_illness_information/',views.admin_illness_information,name='admin_illness_information'),
    path('user_illness_information/',views.user_illness_information,name='user_illness_information'),
    path('admin_ai_analysis/<int:symptom_id>/', views.admin_ai_analysis, name='admin_ai_analysis'),
    path("user_ai_analysis/<int:symptom_id>/", views.user_run_ai_analysis, name="user_ai_analysis"),
    path('admin_latest-analysis/', views.admin_latest_ai_analysis, name='admin_latest_ai_analysis'),
    path('user_latest-analysis/', views.user_latest_ai_analysis, name='user_latest_ai_analysis'),
   
    path('sign-out/',views.signout,name='sign-out'),
]