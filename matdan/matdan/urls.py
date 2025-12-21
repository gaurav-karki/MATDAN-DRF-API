"""
URL configuration for matdan project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# API endpoints under a versioned path
api_urlpatterns = [
    path('accounts/', include('accounts.urls')),
    path('blockchain/',include('blockchain.urls')),
    path('elections/', include('elections.urls')),
    path('voting/', include('voting.urls')),
    

]
urlpatterns = [
    # all api endpoints are now prefixed with 'api/'
    path('api/v1/', include(api_urlpatterns)),

    #Non-API paths like admin and auth
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
