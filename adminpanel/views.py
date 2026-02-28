from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from users.decorators import admin_required
from users.models import User
from properties.models import Property


@login_required
@admin_required
def admin_dashboard(request):
    """Admin dashboard with system overview."""
    total_users = User.objects.count()
    total_tenants = User.objects.filter(role=User.Role.TENANT).count()
    total_owners = User.objects.filter(role=User.Role.OWNER).count()
    total_properties = Property.objects.count()
    available_properties = Property.objects.filter(status=Property.Status.AVAILABLE).count()
    rented_properties = Property.objects.filter(status=Property.Status.RENTED).count()

    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_properties = Property.objects.select_related('owner').order_by('-created_at')[:5]

    context = {
        'total_users': total_users,
        'total_tenants': total_tenants,
        'total_owners': total_owners,
        'total_properties': total_properties,
        'available_properties': available_properties,
        'rented_properties': rented_properties,
        'recent_users': recent_users,
        'recent_properties': recent_properties,
    }
    return render(request, 'adminpanel/dashboard.html', context)


@login_required
@admin_required
def manage_users(request):
    """List and manage all users."""
    role_filter = request.GET.get('role', '')
    users = User.objects.all()

    if role_filter:
        users = users.filter(role=role_filter)

    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'adminpanel/manage_users.html', {
        'users': page_obj,
        'role_filter': role_filter,
        'current_role': role_filter,
    })


@login_required
@admin_required
def toggle_user_active(request, pk):
    """Activate or deactivate a user account."""
    user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        if user == request.user:
            messages.error(request, 'You cannot deactivate your own account.')
        else:
            user.is_active = not user.is_active
            user.save()
            status = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'User {user.username} has been {status}.')

    return redirect('adminpanel:manage_users')


@login_required
@admin_required
def manage_properties(request):
    """List and manage all property listings."""
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    properties = Property.objects.select_related('owner').all()

    if status_filter:
        properties = properties.filter(status=status_filter)
    if type_filter:
        properties = properties.filter(property_type=type_filter)

    paginator = Paginator(properties, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'adminpanel/manage_properties.html', {
        'properties': page_obj,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'property_types': Property.PropertyType.choices,
        'status_choices': Property.Status.choices,
    })


@login_required
@admin_required
def toggle_property_approval(request, pk):
    """Approve or disapprove a property listing."""
    property_obj = get_object_or_404(Property, pk=pk)

    if request.method == 'POST':
        property_obj.is_approved = not property_obj.is_approved
        property_obj.save()
        status = 'approved' if property_obj.is_approved else 'disapproved'
        messages.success(request, f'Property "{property_obj.title}" has been {status}.')

    return redirect('adminpanel:manage_properties')


@login_required
@admin_required
def delete_property(request, pk):
    """Admin delete a property listing."""
    property_obj = get_object_or_404(Property, pk=pk)

    if request.method == 'POST':
        title = property_obj.title
        property_obj.delete()
        messages.success(request, f'Property "{title}" has been deleted.')

    return redirect('adminpanel:manage_properties')
