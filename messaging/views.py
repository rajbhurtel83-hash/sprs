from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.db.models import Q
from .models import Conversation, Message
from .forms import MessageForm
from properties.models import Property


@login_required
def inbox(request):
    """Display user's message inbox with all conversations."""
    conversations = Conversation.objects.filter(
        Q(tenant=request.user) | Q(owner=request.user)
    ).select_related('property', 'tenant', 'owner').prefetch_related('messages')

    conversation_data = []
    for conv in conversations:
        other_user = conv.owner if conv.tenant == request.user else conv.tenant
        last_msg = conv.last_message
        unread = conv.unread_count_for(request.user)
        conversation_data.append({
            'conversation': conv,
            'other_user': other_user,
            'last_message': last_msg,
            'unread_count': unread,
        })

    return render(request, 'messaging/inbox.html', {
        'conversation_data': conversation_data,
    })


@login_required
def conversation_detail(request, pk):
    """Display conversation thread and handle replies."""
    conversation = get_object_or_404(
        Conversation.objects.select_related('property', 'tenant', 'owner'),
        pk=pk,
    )

    # Ensure user is part of this conversation
    if request.user != conversation.tenant and request.user != conversation.owner:
        django_messages.error(request, 'You do not have access to this conversation.')
        return redirect('messaging:inbox')

    # Mark unread messages as read
    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            # Update conversation timestamp
            conversation.save()
            return redirect('messaging:conversation', pk=conversation.pk)
    else:
        form = MessageForm()

    other_user = conversation.owner if conversation.tenant == request.user else conversation.tenant
    all_messages = conversation.messages.select_related('sender').all()

    return render(request, 'messaging/conversation.html', {
        'conversation': conversation,
        'messages_list': all_messages,
        'form': form,
        'other_user': other_user,
    })


@login_required
def start_conversation(request, property_pk):
    """Start a new conversation about a property (tenant initiates)."""
    property_obj = get_object_or_404(Property, pk=property_pk)

    # Don't allow owner to message themselves
    if request.user == property_obj.owner:
        django_messages.warning(request, 'You cannot send a message to yourself.')
        return redirect('properties:detail', pk=property_pk)

    # Check if conversation already exists
    conversation = Conversation.objects.filter(
        property=property_obj,
        tenant=request.user,
    ).first()

    if conversation:
        return redirect('messaging:conversation', pk=conversation.pk)

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            conversation = Conversation.objects.create(
                property=property_obj,
                tenant=request.user,
                owner=property_obj.owner,
            )
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            django_messages.success(request, 'Message sent to the property owner.')
            return redirect('messaging:conversation', pk=conversation.pk)
    else:
        form = MessageForm()

    return render(request, 'messaging/start_conversation.html', {
        'form': form,
        'property': property_obj,
    })
