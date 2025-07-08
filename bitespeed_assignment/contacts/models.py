from django.db import models


class LinkPrecedence(models.TextChoices):
    PRIMARY = "primary", "Primary"
    SECONDARY = "secondary", "Secondary"

class Contact(models.Model):
    """Represents a user's contact that can be linked to other contacts."""

    phone_number = models.CharField(
        max_length=20, null=True, blank=True, db_column="phoneNumber"
    )
    email = models.EmailField(null=True, blank=True)

    linked_contact = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="secondary_contacts",
        db_column="linkedId",
    )

    link_precedence = models.CharField(
        max_length=10,
        choices=LinkPrecedence.choices,
        default=LinkPrecedence.PRIMARY,
        db_column="linkPrecedence",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_column="createdAt")
    updated_at = models.DateTimeField(auto_now=True, db_column="updatedAt")
    deleted_at = models.DateTimeField(null=True, blank=True, db_column="deletedAt")

    class Meta:
        db_table = "contact"

    def __str__(self):
        return f"{self.phone_number or ''} - {self.email or ''}"
