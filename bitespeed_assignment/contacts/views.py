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
            else:
                candidate = contacts.earliest('created_at')

                # If the oldest matched contact is SECONDARY, its linked_contact is the true primary
                primary = (
                    candidate.linked_contact if candidate.link_precedence == LinkPrecedence.SECONDARY and candidate.linked_contact_id else candidate
                )

                # Make sure every contact that shares the same email or phone is linked to this primary
                Contact.objects\
                    .filter(Q(email=primary.email) | Q(phone_number=primary.phone_number))\
                    .exclude(pk=primary.pk)\
                    .update(
                        link_precedence=LinkPrecedence.SECONDARY,
                        linked_contact=primary
                    )
                # create a secondary if the incoming email/phone is new to this cluster
                if (email and not contacts.filter(email=email).exists()) \
                or (phone_no and not contacts.filter(phone_number=phone_no).exists()):
                    Contact.objects.create(
                        email=email,
                        phone_number=phone_no,
                        link_precedence=LinkPrecedence.SECONDARY,
                        linked_contact=primary,
                    )

        # Build response payload: include primary plus all linked secondaries, ordered oldest→newest
        group = (
            Contact.objects.filter(Q(pk=primary.pk) | Q(linked_contact=primary))
            .order_by("created_at")
        )

        emails, phones, secondary_ids = [], [], []

        for idx, contact in enumerate(group):
            # oldest (idx==0) is primary, rest are secondary ids list
            if idx > 0:
                secondary_ids.append(contact.pk)

            if contact.email and contact.email not in emails:
                emails.append(contact.email)
            if contact.phone_number and contact.phone_number not in phones:
                phones.append(contact.phone_number)

        response_payload = {
            "contact": {
                "primaryContactId": primary.pk,
                "emails": emails,
                "phoneNumbers": phones,
                "secondaryContactIds": secondary_ids,
            }
        }

        return Response(response_payload, status=status.HTTP_200_OK)
