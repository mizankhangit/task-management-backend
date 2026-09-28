from django.urls import path
from rest_framework.routers import DefaultRouter
from .consumers import ProjectConsumer
from .views import TaskViewSet

router = DefaultRouter()

router.register("tasks", TaskViewSet, basename="task")

urlpatterns = router.urls