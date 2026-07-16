import json
import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST

# Try to import advanced engine first, fall back to basic
try:
    from .engine_advanced import (
        get_advanced_chatbot_response,
        search_properties_advanced,
        get_property_recommendations,
        get_area_insights
    )
    USE_ADVANCED = True
except ImportError:
    from .engine import get_chatbot_response, search_properties_with_filters
    USE_ADVANCED = False


logger = logging.getLogger(__name__)

MAX_REQUEST_BODY_BYTES = 32 * 1024
MAX_MESSAGE_LENGTH = 1200
MAX_HISTORY_ITEMS = 12
MAX_HISTORY_ITEM_LENGTH = 1200
ALLOWED_LANGUAGES = {'auto', 'english', 'nepali'}

RATE_LIMITS = {
    'chat': (60, 60),
    'recommendations': (20, 60),
    'area_insights': (20, 60),
}


def _client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _is_request_too_large(request):
    try:
        content_length = int(request.META.get('CONTENT_LENGTH') or 0)
    except (TypeError, ValueError):
        content_length = 0
    return content_length > MAX_REQUEST_BODY_BYTES


def _is_rate_limited(request, scope, limit, window_seconds):
    if request.user.is_authenticated:
        identity = f'user:{request.user.pk}'
    else:
        identity = f'ip:{_client_ip(request)}'

    key = f'chatbot-rate:{scope}:{identity}'
    if cache.add(key, 1, timeout=window_seconds):
        return False

    try:
        current = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        return False

    return current > limit


def _sanitize_history(raw_history):
    clean_history = []
    if not isinstance(raw_history, list):
        return clean_history

    for item in raw_history[-MAX_HISTORY_ITEMS:]:
        if not isinstance(item, dict):
            continue

        role = item.get('role')
        content = item.get('content', '')
        if role not in {'system', 'user', 'assistant'}:
            continue
        if not isinstance(content, str):
            continue

        safe_content = content.strip()[:MAX_HISTORY_ITEM_LENGTH]
        if not safe_content:
            continue

        clean_history.append({'role': role, 'content': safe_content})

    return clean_history


def _sanitize_location(raw_location):
    if not isinstance(raw_location, dict):
        return None

    safe_location = {}

    district = raw_location.get('district')
    if isinstance(district, str) and district.strip():
        safe_location['district'] = district.strip()[:64]

    latitude = raw_location.get('lat')
    longitude = raw_location.get('lng')
    try:
        if latitude is not None:
            lat = float(latitude)
            if -90 <= lat <= 90:
                safe_location['lat'] = lat
        if longitude is not None:
            lng = float(longitude)
            if -180 <= lng <= 180:
                safe_location['lng'] = lng
    except (TypeError, ValueError):
        return None

    return safe_location or None


@require_POST
def chat(request):
    """Handle chatbot messages via AJAX with advanced AI features."""
    if _is_request_too_large(request):
        return JsonResponse({'error': 'Payload too large'}, status=413)

    limit, window = RATE_LIMITS['chat']
    if _is_rate_limited(request, 'chat', limit, window):
        return JsonResponse({'error': 'Too many requests. Please try again shortly.'}, status=429)

    try:
        body = json.loads(request.body)
        user_message = body.get('message', '')
        conversation_history = _sanitize_history(body.get('history', []))
        user_location = _sanitize_location(body.get('location'))
        language_preference = body.get('language', 'auto')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not isinstance(user_message, str):
        return JsonResponse({'error': 'Message must be text'}, status=400)
    user_message = user_message.strip()

    if not user_message:
        return JsonResponse({'error': 'Message is required'}, status=400)
    if len(user_message) > MAX_MESSAGE_LENGTH:
        return JsonResponse({'error': f'Message too long (max {MAX_MESSAGE_LENGTH} characters)'}, status=400)

    if language_preference not in ALLOWED_LANGUAGES:
        language_preference = 'auto'

    try:
        if USE_ADVANCED:
            result = get_advanced_chatbot_response(
                user_message,
                conversation_history,
                user_location,
                language_preference
            )
        else:
            result = get_chatbot_response(user_message, conversation_history)
            result['intent'] = 'search' if result.get('filters') else 'question'
            result['suggestions'] = []
    except Exception:
        logger.exception('Chatbot response generation failed')
        result = {
            'response': "I apologize, but I'm having trouble processing your request. Please try again or rephrase your question.",
            'filters': None,
            'intent': 'error',
            'suggestions': ['Try again', 'Search properties', 'Get help']
        }

    properties = []
    if result.get('filters'):
        try:
            if USE_ADVANCED:
                properties = search_properties_advanced(result['filters'], limit=8)
            else:
                # Legacy format
                qs = search_properties_with_filters(result['filters'])
                for prop in qs:
                    img = prop.primary_image
                    properties.append({
                        'id': prop.pk,
                        'title': prop.title,
                        'property_type': prop.get_property_type_display(),
                        'district': prop.district,
                        'municipality': prop.municipality or '',
                        'ward_number': prop.ward_number,
                        'price': str(prop.price),
                        'num_rooms': prop.num_rooms,
                        'rating': prop.average_rating,
                        'image': img.image.url if img else None,
                        'url': prop.get_absolute_url(),
                        'has_location': prop.has_location,
                        'latitude': float(prop.latitude) if prop.latitude else None,
                        'longitude': float(prop.longitude) if prop.longitude else None,
                    })
        except Exception:
            logger.exception('Property search failed for chatbot request')

        if not properties:
            is_nepali = result.get('detected_language') == 'nepali'
            no_result_msg = (
                '\n\nमाफ गर्नुहोस्, उक्त मापदण्ड अनुसार कुनै सम्पत्ति भेटिएन। प्रयास गर्नुहोस्:\n• बजेट बढाउनुहोस्\n• अर्को जिल्ला हेर्नुहोस्\n• फिल्टर घटाउनुहोस्'
                if is_nepali else
                "\n\nSorry, no properties found matching those criteria. Try:\n• Expanding your budget\n• Searching in a nearby district\n• Removing some filters"
            )
            result['response'] += no_result_msg
    elif USE_ADVANCED and result.get('intent') in {'greeting', 'help', 'recommendation'}:
        # Show smart recommendations when user is exploring rather than filtering.
        try:
            properties = get_property_recommendations(limit=4)
        except Exception:
            logger.exception('Recommendation fallback failed during chatbot response')

    return JsonResponse({
        'response': result.get('response', 'Unable to process request right now.'),
        'properties': properties,
        'filters': result.get('filters'),
        'intent': result.get('intent', 'question'),
        'suggestions': result.get('suggestions', []),
        'property_count': len(properties),
        'detected_language': result.get('detected_language', 'english'),
    })


@require_POST
def get_recommendations(request):
    """Get AI-powered property recommendations."""
    if not USE_ADVANCED:
        return JsonResponse({'error': 'Advanced features not available'}, status=503)

    if _is_request_too_large(request):
        return JsonResponse({'error': 'Payload too large'}, status=413)

    limit, window = RATE_LIMITS['recommendations']
    if _is_rate_limited(request, 'recommendations', limit, window):
        return JsonResponse({'error': 'Too many requests. Please try again shortly.'}, status=429)
    
    try:
        body = json.loads(request.body)
        preferences = body.get('preferences', {})
        viewed = body.get('viewed_properties', [])
    except (json.JSONDecodeError, AttributeError):
        preferences = {}
        viewed = []

    if not isinstance(preferences, dict):
        preferences = {}

    if isinstance(viewed, list):
        clean_viewed = []
        for value in viewed[:100]:
            try:
                clean_viewed.append(int(value))
            except (TypeError, ValueError):
                continue
        viewed = clean_viewed
    else:
        viewed = []
    
    try:
        recommendations = get_property_recommendations(
            user_preferences=preferences,
            viewed_properties=viewed,
            limit=6
        )
        
        return JsonResponse({
            'recommendations': recommendations,
            'count': len(recommendations)
        })
    except Exception:
        logger.exception('Failed to generate chatbot recommendations')
        return JsonResponse({'error': 'Unable to load recommendations right now.'}, status=500)


@require_POST  
def area_insights(request):
    """Get insights about a specific area."""
    if not USE_ADVANCED:
        return JsonResponse({'error': 'Advanced features not available'}, status=503)

    if _is_request_too_large(request):
        return JsonResponse({'error': 'Payload too large'}, status=413)

    limit, window = RATE_LIMITS['area_insights']
    if _is_rate_limited(request, 'area_insights', limit, window):
        return JsonResponse({'error': 'Too many requests. Please try again shortly.'}, status=429)
    
    try:
        body = json.loads(request.body)
        district = body.get('district', '')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not isinstance(district, str):
        return JsonResponse({'error': 'District must be text'}, status=400)
    district = district.strip()[:64]
    
    if not district:
        return JsonResponse({'error': 'District is required'}, status=400)
    
    try:
        insights = get_area_insights(district)
        return JsonResponse(insights)
    except Exception:
        logger.exception('Failed to generate area insights for district=%s', district)
        return JsonResponse({'error': 'Unable to fetch area insights right now.'}, status=500)
