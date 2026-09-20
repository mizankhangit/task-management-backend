from apps.projects.services import accept_project_invitation
from apps.projects.serializers import AcceptInvitationSerializer
from rest_framework.views import APIView
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework import status

class AcceptProjectInvitationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)

        serializer.is_valid(
            raise_exception=True
        )

        try:
            membership = (
                accept_project_invitation(
                    token=serializer.validated_data[
                        "token"
                    ],
                    user=request.user,
                )
            )

        except ValueError as exc:
            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": (
                    "Invitation accepted."
                ),
                "project_id": (
                    membership.project_id
                ),
                "role": membership.role,
            },
            status=status.HTTP_200_OK,
        )