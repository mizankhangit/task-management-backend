import pytest

from apps.projects.models import Project


@pytest.mark.django_db
def test_project_string_representation(
    django_user_model,
):
    user = django_user_model.objects.create_user(
        username="mizan",
        password="password123",
    )

    project = Project.objects.create(
        owner=user,
        name="Website",
    )

    assert str(project) == "Website"