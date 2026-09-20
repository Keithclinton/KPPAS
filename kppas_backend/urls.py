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
from .views import (
    feedback_view, ussd_feedback_view, data_access_view,
    promise_registry_view, county_promises_view, county_brief_view, promise_detail_view,
)
from .api import open_data_api

urlpatterns = [
    path('', promise_registry_view, name='promise_registry'),
    path('promises/<str:county>/', county_promises_view, name='county_promises'),
    path('promises/<str:county>/brief/', county_brief_view, name='county_brief'),
    path('promises/<str:county>/<int:promise_id>/', promise_detail_view, name='promise_detail'),
    path('admin/', admin.site.urls),
    path('feedback/', feedback_view, name='feedback'),
    path('data/access/', data_access_view, name='data_access'),
    path('api/open-data/', open_data_api, name='open_data_api'),
    path('ussd/feedback/', ussd_feedback_view, name='ussd_feedback'),
]
