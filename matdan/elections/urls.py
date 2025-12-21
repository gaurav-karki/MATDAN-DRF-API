from rest_framework.routers import DefaultRouter
from .views import ElectionCreationView, CandidateListByElectionView
from django.urls import path

app_name = 'elections'

router = DefaultRouter()
router.register(r'', ElectionCreationView, basename='election')

urlpatterns = router.urls

urlpatterns += [
    path('<uuid:election_id>/candidates', CandidateListByElectionView.as_view(), name='election-candidates'),
]
