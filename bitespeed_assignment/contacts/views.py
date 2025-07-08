from django.db import transaction
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser

from .models import Contact, LinkPrecedence

class IdentifyView(APIView):
    parser_classes = [JSONParser]

    def post(self, request, *args, **kwargs):
        # Extract request payload
        email = request.data.get("email")
        phone_no = request.data.get("phoneNumber")

        if not email and not phone_no:
            return Response(
                {"error": "At least one of 'email' or 'phoneNumber' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Only filter on provided fields
            filters = Q()
            if email:
                filters |= Q(email=email)
            if phone_no:
                filters |= Q(phone_number=phone_no)
            contacts = Contact.objects.filter(filters)

            # If no contacts found, create a new primary contact
            if not contacts.exists():
                primary = Contact.objects.create(
                    email=email,
                    phone_number=phone_no,
                    link_precedence=LinkPrecedence.PRIMARY,
                )
                secondaries = []
            else:
                primary = contacts.earliest('created_at')
                Contact.objects\
                    .filter(Q(email=primary.email) | Q(phone_number=primary.phone_number))\
                    .exclude(pk=primary.pk)\
                    .update(
                        link_precedence=LinkPrecedence.SECONDARY,
                        linked_contact=primary
                    )
                secondaries = list(contacts.exclude(pk=primary.pk))

                # if payload has new email/phone not in contacts → create one more secondary
                if (email and not contacts.filter(email=email).exists()) \
                or (phone_no and not contacts.filter(phone_number=phone_no).exists()):
                    c = Contact.objects.create(
                        email=email, phone_number=phone_no,
                        link_precedence=LinkPrecedence.SECONDARY,
                        linked_contact=primary
                    )
                    secondaries.append(c)

        # Build response payload: include primary plus all secondaries linked to it
        group = Contact.objects.filter(
            Q(pk=primary.pk) | Q(linked_contact=primary)
        )

        response_payload = {
            "contact": {
                "primaryContactId": primary.pk,
                "emails":     list(group.values_list("email", flat=True).distinct()),
                "phoneNumbers": list(group.values_list("phone_number", flat=True).distinct()),
                "secondaryContactIds": list(
                    group.exclude(pk=primary.pk)
                         .values_list("pk", flat=True)
                ),
            }
        }

        return Response(response_payload, status=status.HTTP_200_OK)
