from rest_framework.routers import DefaultRouter

from .views import ProjectViewSet, ProjectMembershipViewSet


router = DefaultRouter()

router.register(
    "projects",
    ProjectViewSet,
    basename="project",
)
router.register(
    "project-memberships",
    ProjectMembershipViewSet,
    basename="project-membership",
)

urlpatterns = router.urls