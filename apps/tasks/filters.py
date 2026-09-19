import django_filters

from django.utils import timezone

from .models import Task


class TaskFilter(django_filters.FilterSet):

    due_before = django_filters.DateFilter(
        field_name="due_date",
        lookup_expr="lte",
    )

    due_after = django_filters.DateFilter(
        field_name="due_date",
        lookup_expr="gte",
    )

    overdue = django_filters.BooleanFilter(
        method="filter_overdue",
    )

    has_due_date = django_filters.BooleanFilter(
        method="filter_has_due_date",
    )

    assigned_to_me = django_filters.BooleanFilter(
        method="filter_assigned_to_me",
    )

    class Meta:
        model = Task

        fields = [
            "project",
            "status",
            "priority",
            "completed",
            "assignee",
            "assigned_to_me",
            "due_before",
            "due_after",
            "overdue",
            "has_due_date",
        ]

    def filter_assigned_to_me(
        self,
        queryset,
        name,
        value,
    ):
        if value is True and self.request and self.request.user.is_authenticated:
            return queryset.filter(assignee=self.request.user)
        return queryset

    def filter_overdue(
        self,
        queryset,
        name,
        value,
    ):
        if value is not True:
            return queryset

        today = timezone.localdate()

        return queryset.filter(
            due_date__lt=today,
            completed=False,
        )

    def filter_has_due_date(
        self,
        queryset,
        name,
        value,
    ):
        if value is True:
            return queryset.filter(
                due_date__isnull=False
            )

        if value is False:
            return queryset.filter(
                due_date__isnull=True
            )

        return queryset