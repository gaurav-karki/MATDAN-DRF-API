from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CandidateListByElectionView, ElectionCreationView, ElectionUpdateView

app_name = "elections"

router = DefaultRouter()
router.register(r"", ElectionCreationView, basename="CreateElection")


urlpatterns = router.urls

urlpatterns += [
    path(
        "<uuid:election_id>/candidates",
        CandidateListByElectionView.as_view(),
        name="election-candidates",
    ),
    path("<pk>/update", ElectionUpdateView.as_view(), name="update-election"),
]
