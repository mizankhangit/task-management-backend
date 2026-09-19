from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated


class UserSearchSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "name",
        ]

    def get_name(self, obj):
        full_name = obj.get_full_name()
        return full_name if full_name else obj.username.capitalize()


class UserSearchView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSearchSerializer

    def get_queryset(self):
        query = self.request.query_params.get("search", "").strip()
        queryset = User.objects.filter(is_active=True).exclude(id=self.request.user.id)
        if query:
            queryset = queryset.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )
        return queryset.order_by("username")[:20]
