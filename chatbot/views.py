import json
import traceback
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

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


@require_POST
def chat(request):
    """Handle chatbot messages via AJAX with advanced AI features."""
    try:
        body = json.loads(request.body)
        user_message = body.get('message', '').strip()
        conversation_history = body.get('history', [])
        user_location = body.get('location')  # Optional: {district: "...", lat: ..., lng: ...}
        language_preference = body.get('language', 'auto')  # 'auto' | 'english' | 'nepali'
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not user_message:
        return JsonResponse({'error': 'Message is required'}, status=400)

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
    except Exception as e:
        print(f"Chatbot error: {e}")
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
        except Exception as e:
            print(f"Property search error: {e}")

        if not properties:
            is_nepali = result.get('detected_language') == 'nepali'
            no_result_msg = (
                '\n\nमाफ गर्नुहोस्, उक्त मापदण्ड अनुसार कुनै सम्पत्ति भेटिएन। प्रयास गर्नुहोस्:\n• बजेट बढाउनुहोस्\n• अर्को जिल्ला हेर्नुहोस्\n• फिल्टर घटाउनुहोस्'
                if is_nepali else
                "\n\nSorry, no properties found matching those criteria. Try:\n• Expanding your budget\n• Searching in a nearby district\n• Removing some filters"
            )
            result['response'] += no_result_msg

    return JsonResponse({
        'response': result['response'],
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
    
    try:
        body = json.loads(request.body)
        preferences = body.get('preferences', {})
        viewed = body.get('viewed_properties', [])
    except (json.JSONDecodeError, AttributeError):
        preferences = {}
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
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST  
def area_insights(request):
    """Get insights about a specific area."""
    if not USE_ADVANCED:
        return JsonResponse({'error': 'Advanced features not available'}, status=503)
    
    try:
        body = json.loads(request.body)
        district = body.get('district', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    if not district:
        return JsonResponse({'error': 'District is required'}, status=400)
    
    try:
        insights = get_area_insights(district)
        return JsonResponse(insights)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
