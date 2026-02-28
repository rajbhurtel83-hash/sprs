from django.db import models
from django.conf import settings


class Notification(models.Model):
    """System notification for a user."""

    class NotificationType(models.TextChoices):
        MESSAGE = 'message', 'New Message'
        REQUEST = 'request', 'Property Request'
        APPROVAL = 'approval', 'Request Approved'
        REJECTION = 'rejection', 'Request Rejected'
        LISTING = 'listing', 'New Listing'
        REVIEW = 'review', 'New Review'
        SYSTEM = 'system', 'System'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.username}"
