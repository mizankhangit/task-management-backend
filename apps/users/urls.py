from django.urls import path
from .views import UserSearchView

urlpatterns = [
    path("users/", UserSearchView.as_view(), name="user-search"),
]
