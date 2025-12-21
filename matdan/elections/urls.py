from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import ElectionCreationView

router = DefaultRouter()
router.register(r'elections', ElectionCreationView, basename='election')

urlpatterns = router.urls

#urlpatterns = [
    #path('',views.elections_home, name='elections_home'),
    #path('election/',views.ElectionCreationView.as_view(), name='election')
#]
