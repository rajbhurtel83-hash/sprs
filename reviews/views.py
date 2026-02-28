from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from notifications.models import Notification
from properties.models import Property
from reviews.forms import ReviewForm
from reviews.models import Review


@login_required
@require_POST
def add_review(request, property_id):
    property = get_object_or_404(Property, pk=property_id)

    if Review.objects.filter(property=property, reviewer=request.user).exists():
        messages.error(request, "You have already reviewed this property.")
        return redirect('properties:detail', pk=property.pk)

    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.property = property
        review.reviewer = request.user
        review.save()

        Notification.objects.create(
            user=property.owner,
            notification_type=Notification.NotificationType.REVIEW,
            title="New Review",
            message=(
                f"{request.user.username} left a {review.rating}-star review "
                f"on {property.title}"
            ),
            link=property.get_absolute_url(),
        )

        messages.success(request, "Your review has been submitted successfully.")
    return redirect('properties:detail', pk=property.pk)


@login_required
@require_POST
def delete_review(request, pk):
    review = get_object_or_404(Review, pk=pk, reviewer=request.user)
    property_pk = review.property.pk
    review.delete()
    messages.success(request, "Your review has been deleted.")
    return redirect('properties:detail', pk=property_pk)
