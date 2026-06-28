"""
URL configuration for kppas_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from .views import feedback_view, upload_scores_view, dashboard_view, county_detail_view
from .api import health_data_api

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
    path('county/<str:county>/', county_detail_view, name='county_detail'),
    path('admin/', admin.site.urls),
    path('feedback/', feedback_view, name='feedback'),
    path('data/upload/', upload_scores_view, name='upload_scores'),
    path('api/health/', health_data_api, name='health_data_api'),
]
