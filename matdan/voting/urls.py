from django.urls import path

from .views import ElectionResultsView, MyVoteView, VoteCreateView, voting_home

app_name = "voting"

urlpatterns = [
    path("", voting_home, name="voting_home"),
    path("<uuid:election_id>/vote/", VoteCreateView.as_view(), name="cast_vote"),
    path("<uuid:election_id>/my-vote/", MyVoteView.as_view(), name="my_vote"),
    path(
        "<uuid:election_id>/results/",
        ElectionResultsView.as_view(),
        name="election_results",
    ),
]
