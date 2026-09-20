from rest_framework.routers import DefaultRouter

from .views import ProjectViewSet, ProjectMembershipViewSet

from django.urls import path

from .invitation_views import (
    AcceptProjectInvitationView,
)

router = DefaultRouter()
invitation_urlpatterns = [
    path("invitations/accept/", AcceptProjectInvitationView.as_view(), name="accept-invitation"),
]
router.register("projects", ProjectViewSet, basename="project")
router.register("project-memberships", ProjectMembershipViewSet, basename="project-membership")

urlpatterns = router.urls + invitation_urlpatterns