from django.urls import path

from .views import (
    BlockchainElectionStatusView,
    BlockchainResultsView,
    BlockchainStatusView,
    SyncElectionToBlockchainView,
    VerifyVoteView,
)

app_name = "blockchain"


urlpatterns = [
    # Connection status
    path("status/", BlockchainStatusView.as_view(), name="status"),
    # Election management
    path(
        "elections/<uuid:election_id>/sync/",
        SyncElectionToBlockchainView.as_view(),
        name="sync-election",
    ),
    path(
        "elections/<uuid:election_id>/activate/",
        BlockchainElectionStatusView.as_view(),
        name="activate-election",
    ),
    path(
        "elections/<uuid:election_id>/results/",
        BlockchainResultsView.as_view(),
        name="blockchain-results",
    ),
    # Vote verification
    path("votes/verify/", VerifyVoteView.as_view(), name="verify-vote"),
]
