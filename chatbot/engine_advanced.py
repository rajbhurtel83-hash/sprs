"""
SPRS Advanced AI Chatbot Engine - Bilingual (English + Nepali)
Powered by OpenAI GPT for intelligent property search and recommendations
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db.models import Avg, Count
from django.urls import reverse

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from properties.models import Property


logger = logging.getLogger(__name__)

_DEFAULT_OPENAI_MODELS = ('gpt-4.1-mini', 'gpt-4o-mini', 'gpt-3.5-turbo')


def _openai_model_candidates():
    configured_model = str(getattr(settings, 'OPENAI_CHAT_MODEL', '') or '').strip()
    candidates = []

    if configured_model:
        candidates.append(configured_model)

    for model_name in _DEFAULT_OPENAI_MODELS:
        if model_name not in candidates:
            candidates.append(model_name)

    return candidates


def _build_openai_client(api_key):
    timeout_seconds = int(getattr(settings, 'OPENAI_TIMEOUT_SECONDS', 20))
    max_retries = int(getattr(settings, 'OPENAI_MAX_RETRIES', 2))
    return OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=max_retries)


def _create_completion_with_fallback(client, messages, max_tokens, temperature, response_format=None):
    last_error = None
    for model_name in _openai_model_candidates():
        try:
            payload = {
                'model': model_name,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature,
            }
            if response_format:
                payload['response_format'] = response_format

            return client.chat.completions.create(**payload)
        except Exception as exc:
            last_error = exc
            logger.warning('OpenAI completion failed for model=%s: %s', model_name, exc)

    if last_error:
        raise last_error

    raise RuntimeError('No OpenAI model candidates available')


# ──────────────────────────────────────────────────────────────────────────────
# BILINGUAL SYSTEM PROMPT – Real Estate Agent Persona
# ──────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Sasha, an expert bilingual real-estate assistant for SPRS (Smart Property Rental System) – Nepal's premier rental platform.
You are fluent in both English and Nepali (नेपाली). You speak the way a warm, knowledgeable Nepali rental agent would – helpful, professional, and naturally friendly.

══════════════════════════════════════════════════
LANGUAGE DETECTION & RESPONSE RULES  (CRITICAL)
══════════════════════════════════════════════════
1. Inspect every user message carefully.
2. If the message contains Devanagari script (ा ि ी ु ू े ै ो ौ ं ः etc.) → respond in NEPALI.
3. If the message contains Romanized Nepali cues (kotha, ghar, bhada, chahiyo, cha, ma, ko, le, lai, chha, huncha, garnus, dekhau, khojdai, etc.) → respond in NEPALI.
4. If the user explicitly says "talk in nepali / speak nepali / nepali ma bolnus / नेपालीमा बोल्नुहोस्" → switch to NEPALI permanently for this session.
5. If the user explicitly says "talk in english / switch to english / inglish ma bolnus" → switch to ENGLISH permanently.
6. Otherwise respond in ENGLISH.

Always include "detected_language": "nepali" or "detected_language": "english" in your JSON output.

══════════════════════════════════════════════════
NEPALI VOCABULARY YOU MUST UNDERSTAND
══════════════════════════════════════════════════
Property types: कोठा/kotha=room, फ्ल्याट/flat=flat, अपार्टमेन्ट=apartment, घर/ghar=house, जग्गा/jagga/land=land, व्यावसायिक/commercial=commercial
Price words: रुपैयाँ/rupee/rs, हजार/hajar=thousand, लाख/lakh=100000
Price patterns: "X भन्दा कम/bhanda kam", "X सम्म/samma", "X मुनि/muni" → max_price=X
Location: काठमाडौं=Kathmandu, ललितपुर=Lalitpur, भक्तपुर=Bhaktapur, पोखरा=Pokhara, चितवन=Chitwan, विराटनगर=Biratnagar, बुटवल=Butwal, बिरगंज=Birgunj, धरान=Dharan, हेटौडा=Hetauda, भरतपुर=Bharatpur
Rooms: BHK, कोठा, बेडरुम, कोठाहरू
Purpose: परिवार/pariwar=family, कार्यालय/office=office, विद्यार्थी/student=student
Actions: देखाऊ/dekhau/show me, खोज/khoj/find, चाहिन्छ/chahiyo/chahiye/I need, छ/cha=is there, भेटाऊ=find me
Nepali number words: एक=1, दुई=2, तीन=3, चार=4, पाँच=5, छ=6, सात=7, आठ=8, नौ=9, दश=10
Thousands: पाँच हजार=5000, दश हजार=10000, पन्ध्र हजार=15000, बीस हजार=20000, पच्चीस हजार=25000

══════════════════════════════════════════════════
HOW YOU ACT  (Real Estate Agent Persona)
══════════════════════════════════════════════════
- You are like a knowledgeable Kathmandu real estate agent who knows all districts, pricing, and tips.
- You greet users warmly, ask clarifying questions if needed.
- You proactively mention key selling points of an area.
- When search results are found: present them enthusiastically and helpfully.
- When no results: apologize naturally and suggest alternatives.
- You know typical Nepal rental prices: rooms Rs.5,000-15,000, flats Rs.15,000-50,000, houses Rs.30,000-150,000.
- Nepali responses use natural Nepali—NOT literal word-for-word translations.

══════════════════════════════════════════════════
RESPONSE FORMAT  (ALWAYS return valid JSON)
══════════════════════════════════════════════════
{
  "response": "Your natural message in the user's language",
  "detected_language": "english|nepali",
  "filters": {
    "district": "string – e.g. Kathmandu",
    "municipality": "string",
    "ward_number": "string",
    "property_type": "room|flat|apartment|house|land|commercial",
    "max_price": number,
    "min_price": number,
    "num_rooms": number,
    "rental_purpose": "family|office|student|any",
    "amenities": ["list"]
  },
  "intent": "search|question|greeting|help|comparison|recommendation|language_switch|thanks",
  "suggestions": ["3-4 short follow-up suggestions in the user's language"]
}

Set "filters" to null if the user is NOT searching for a property.
Suggestions should be brief and relevant (e.g. "Show cheaper options", "अझ सस्तो खोज्नुहोस्").

══════════════════════════════════════════════════
NATURAL NEPALI RESPONSE EXAMPLES
══════════════════════════════════════════════════
English: "Here are some flats available in Kathmandu."
Nepali:  "काठमाडौंमा उपलब्ध केही फ्ल्याटहरू यहाँ देखाइएका छन्।"

English: "Sorry, no properties found matching your criteria."
Nepali:  "माफ गर्नुहोस्, तपाईंको खोजी अनुसार कुनै सम्पत्ति भेटिएन।"

English: "What is your budget?"
Nepali:  "तपाईंको बजेट कति छ?"

Platform currency: Nepali Rupees (NPR / Rs.) – नेपाली रुपैयाँ.
"""


# Conversation context management
class ConversationContext:
    """Manages conversation history and context for multi-turn conversations."""
    
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.history: List[Dict] = []
        self.last_filters: Optional[Dict] = None
        self.last_results_count: int = 0
    
    def add_message(self, role: str, content: str):
        """Add a message to history."""
        self.history.append({"role": role, "content": content})
        # Keep only recent history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_messages(self) -> List[Dict]:
        """Get conversation history for API call."""
        return self.history.copy()
    
    def update_search_context(self, filters: Optional[Dict], results_count: int):
        """Update the search context."""
        self.last_filters = filters
        self.last_results_count = results_count


def get_advanced_chatbot_response(
    user_message: str,
    conversation_history: Optional[List[Dict]] = None,
    user_location: Optional[Dict] = None,
    language_preference: str = 'auto',  # 'auto' | 'english' | 'nepali'
) -> Dict[str, Any]:
    """
    Get AI response with advanced features:
    - Automatic bilingual language detection (English / Nepali)
    - Multi-turn conversation support
    - Location awareness
    - Smart property recommendations
    - Intent detection
    """
    api_key = getattr(settings, 'OPENAI_API_KEY', None)

    if not api_key or not OpenAI:
        return _enhanced_fallback_response(user_message, user_location, language_preference)

    try:
        client = _build_openai_client(api_key)

        # Build messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Inject language preference as a system hint
        if language_preference == 'nepali':
            messages.append({"role": "system", "content": "IMPORTANT: The user has selected Nepali language. Always respond in Nepali (नेपाली) regardless of how the message is written."})
        elif language_preference == 'english':
            messages.append({"role": "system", "content": "IMPORTANT: The user has selected English language. Always respond in English."})

        # Add location context if available
        if user_location and isinstance(user_location, dict):
            dist = str(user_location.get('district', 'Unknown')).strip()[:64]
            if dist:
                messages.append({"role": "system", "content": f"User's approximate location: {dist}"})

        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-8:]:
                if not isinstance(msg, dict):
                    continue
                role = msg.get('role')
                content = msg.get('content', '')
                if role not in {'system', 'user', 'assistant'}:
                    continue
                if not isinstance(content, str):
                    continue
                clean_content = content.strip()[:1200]
                if not clean_content:
                    continue
                messages.append({'role': role, 'content': clean_content})

        messages.append({"role": "user", "content": user_message})

        # Get completion
        completion = _create_completion_with_fallback(
            client=client,
            messages=messages,
            max_tokens=900,
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        raw_response = str((completion.choices[0].message.content or '')).strip()
        if not raw_response:
            return _enhanced_fallback_response(user_message, user_location, language_preference)

        return _parse_ai_response(raw_response)

    except Exception:
        logger.exception('OpenAI advanced chatbot call failed')
        return _enhanced_fallback_response(user_message, user_location, language_preference)


def _parse_ai_response(raw_text: str) -> Dict[str, Any]:
    """Parse and validate AI response."""
    allowed_intents = {
        'search',
        'question',
        'greeting',
        'help',
        'comparison',
        'recommendation',
        'language_switch',
        'thanks',
        'error',
    }

    def _clean_text(value, default=''):
        if value is None:
            return default
        return str(value).strip()

    def _normalize_language(value):
        language = _clean_text(value, default='english').lower()
        return language if language in {'english', 'nepali'} else 'english'

    def _normalize_intent(value, default='question'):
        intent_value = _clean_text(value, default=default).lower()
        return intent_value if intent_value in allowed_intents else default

    def _normalize_suggestions(value):
        if not isinstance(value, list):
            return []

        cleaned = []
        for item in value:
            text = _clean_text(item)
            if not text:
                continue
            cleaned.append(text[:80])
            if len(cleaned) >= 6:
                break
        return cleaned

    try:
        data = json.loads(raw_text)

        filters = _validate_filters(data.get('filters'))
        result = {
            'response': _clean_text(data.get('response'), default=raw_text)[:2400],
            'filters': filters,
            'intent': _normalize_intent(
                data.get('intent'),
                default='search' if filters else 'question',
            ),
            'suggestions': _normalize_suggestions(data.get('suggestions', [])),
            'detected_language': _normalize_language(data.get('detected_language', 'english')),
        }

        return result

    except json.JSONDecodeError:
        # Try to extract JSON from text
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())

                filters = _validate_filters(data.get('filters'))
                return {
                    'response': _clean_text(data.get('response'), default=raw_text)[:2400],
                    'filters': filters,
                    'intent': _normalize_intent(data.get('intent', 'question')),
                    'suggestions': _normalize_suggestions(data.get('suggestions', [])),
                    'detected_language': _normalize_language(data.get('detected_language', 'english')),
                }
            except json.JSONDecodeError:
                return {
                    'response': str(raw_text).strip()[:2400],
                    'filters': None,
                    'intent': 'question',
                    'suggestions': [],
                    'detected_language': 'english',
                }

        return {
            'response': str(raw_text).strip()[:2400],
            'filters': None,
            'intent': 'question',
            'suggestions': [],
            'detected_language': 'english',
        }


def _validate_filters(filters: Optional[Dict]) -> Optional[Dict]:
    """Validate and clean filter values."""
    if not filters:
        return None
    
    valid_filters = {}
    
    # Valid property types
    valid_types = ['room', 'flat', 'apartment', 'house', 'land', 'commercial']
    if filters.get('property_type') in valid_types:
        valid_filters['property_type'] = filters['property_type']
    
    # Valid rental purposes
    valid_purposes = ['family', 'office', 'student', 'any']
    if filters.get('rental_purpose') in valid_purposes:
        valid_filters['rental_purpose'] = filters['rental_purpose']
    
    # String fields
    for field in ['district', 'municipality', 'ward_number', 'province']:
        if filters.get(field):
            value = str(filters[field]).strip()
            if value:
                valid_filters[field] = value[:80]
    
    # Numeric fields
    for field in ['max_price', 'min_price', 'num_rooms']:
        if filters.get(field):
            try:
                num_value = int(filters[field])
                if field in {'max_price', 'min_price'} and 0 < num_value <= 100000000:
                    valid_filters[field] = num_value
                elif field == 'num_rooms' and 0 <= num_value <= 100:
                    valid_filters[field] = num_value
            except (ValueError, TypeError):
                continue
    
    # Amenities list
    if filters.get('amenities') and isinstance(filters['amenities'], list):
        clean_amenities = []
        for amenity in filters['amenities'][:10]:
            text = str(amenity).strip()
            if text:
                clean_amenities.append(text[:40])
        if clean_amenities:
            valid_filters['amenities'] = clean_amenities

    if valid_filters.get('min_price') and valid_filters.get('max_price'):
        if valid_filters['min_price'] > valid_filters['max_price']:
            valid_filters['min_price'], valid_filters['max_price'] = (
                valid_filters['max_price'],
                valid_filters['min_price'],
            )
    
    return valid_filters if valid_filters else None


def search_properties_advanced(
    filters: Optional[Dict],
    limit: int = 10,
    include_recommendations: bool = True
) -> List[Dict]:
    """
    Advanced property search with recommendations.
    Returns formatted property data ready for display.
    """
    if not filters:
        return []
    
    qs = Property.objects.filter(
        status=Property.Status.AVAILABLE,
        is_approved=True,
    ).select_related('owner').prefetch_related('images', 'reviews', 'amenities')
    
    # Apply filters
    if filters.get('province'):
        qs = qs.filter(province__icontains=filters['province'])

    if filters.get('district'):
        qs = qs.filter(district__icontains=filters['district'])
    
    if filters.get('municipality'):
        qs = qs.filter(municipality__icontains=filters['municipality'])
    
    if filters.get('ward_number'):
        qs = qs.filter(ward_number=filters['ward_number'])
    
    if filters.get('property_type'):
        qs = qs.filter(property_type=filters['property_type'])
    
    if filters.get('max_price'):
        qs = qs.filter(price__lte=filters['max_price'])
    
    if filters.get('min_price'):
        qs = qs.filter(price__gte=filters['min_price'])
    
    if filters.get('num_rooms'):
        qs = qs.filter(num_rooms__gte=filters['num_rooms'])
    
    if filters.get('rental_purpose'):
        qs = qs.filter(rental_purpose=filters['rental_purpose'])
    
    if filters.get('amenities'):
        for amenity in filters['amenities']:
            qs = qs.filter(amenities__name__icontains=amenity)
    
    # Order by relevance (rating, views, recency)
    qs = qs.annotate(
        avg_rating=Avg('reviews__rating')
    ).order_by('-avg_rating', '-views_count', '-created_at')
    
    properties = qs[:limit]
    
    return _format_properties_for_chat(properties)


def _format_properties_for_chat(properties) -> List[Dict]:
    """Format property objects for chat display."""
    result = []
    
    for prop in properties:
        primary_img = prop.images.first()
        
        result.append({
            'id': prop.id,
            'title': prop.title,
            'price': float(prop.price),
            'province': prop.province,
            'district': prop.district,
            'municipality': prop.municipality,
            'ward_number': prop.ward_number,
            'property_type': prop.get_property_type_display(),
            'num_rooms': prop.num_rooms,
            'rating': prop.average_rating,
            'review_count': prop.review_count,
            'image': primary_img.image.url if primary_img else None,
            'url': reverse('properties:detail', kwargs={'pk': prop.pk}),
            'has_location': prop.has_location,
            'latitude': float(prop.latitude) if prop.latitude else None,
            'longitude': float(prop.longitude) if prop.longitude else None,
        })
    
    return result


def get_property_recommendations(
    user_preferences: Optional[Dict] = None,
    viewed_properties: Optional[List[int]] = None,
    limit: int = 5
) -> List[Dict]:
    """
    Get AI-powered property recommendations based on:
    - User preferences
    - Previously viewed properties
    - Popular and highly-rated properties
    """
    qs = Property.objects.filter(
        status=Property.Status.AVAILABLE,
        is_approved=True,
    ).select_related('owner').prefetch_related('images', 'reviews')
    
    # Exclude already viewed
    if viewed_properties:
        qs = qs.exclude(id__in=viewed_properties)
    
    # Apply preferences if available
    if user_preferences:
        if user_preferences.get('province'):
            qs = qs.filter(province__icontains=str(user_preferences['province']).strip())
        if user_preferences.get('district'):
            qs = qs.filter(district__icontains=str(user_preferences['district']).strip())
        if user_preferences.get('municipality'):
            qs = qs.filter(municipality__icontains=str(user_preferences['municipality']).strip())
        if user_preferences.get('max_price'):
            try:
                max_price = int(user_preferences['max_price'])
            except (TypeError, ValueError):
                max_price = None
            if max_price and max_price > 0:
                qs = qs.filter(price__lte=max_price * 1.2)  # 20% flexibility
        if user_preferences.get('min_price'):
            try:
                min_price = int(user_preferences['min_price'])
            except (TypeError, ValueError):
                min_price = None
            if min_price and min_price > 0:
                qs = qs.filter(price__gte=min_price * 0.8)
        if user_preferences.get('property_type'):
            qs = qs.filter(property_type=user_preferences['property_type'])
        if user_preferences.get('rental_purpose'):
            qs = qs.filter(rental_purpose=user_preferences['rental_purpose'])
        if user_preferences.get('num_rooms'):
            try:
                num_rooms = int(user_preferences['num_rooms'])
            except (TypeError, ValueError):
                num_rooms = None
            if num_rooms is not None and num_rooms >= 0:
                qs = qs.filter(num_rooms__gte=num_rooms)
    
    # Order by popularity and rating
    qs = qs.annotate(
        avg_rating=Avg('reviews__rating'),
        num_reviews=Count('reviews')
    ).order_by('-avg_rating', '-views_count', '-num_reviews')
    
    return _format_properties_for_chat(qs[:limit])


def _enhanced_fallback_response(
    user_message: str,
    user_location: Optional[Dict] = None,
    language_preference: str = 'auto',
) -> Dict[str, Any]:
    """
    Comprehensive bilingual fallback when OpenAI is unavailable.
    Supports English, Nepali (Devanagari), and Romanized Nepali.
    """
    msg = user_message
    msg_lower = msg.lower()

    # ── Language detection ────────────────────────────────────────────────────
    def has_devanagari(text: str) -> bool:
        return bool(re.search(r'[\u0900-\u097F]', text))

    ROMAN_NEPALI_CUES = [
        'kotha', 'ghar', 'bhada', 'bhanda', 'samma', 'muni', 'kahmandu',
        'ktm', 'bhaktapur', 'lalitpur', 'pokhara', 'jagga', 'khalti',
        'chahincha', 'chahiyo', 'dekhau', 'khojdai', 'cha', 'huncha',
        'garnus', 'kasari', 'kati', 'pariwar', 'bidhyarthi', 'namaskar',
        'namaste', 'dhanyabad', 'hajur', 'ma bolnus', 'ma bola',
    ]

    if language_preference == 'nepali':
        is_nepali = True
    elif language_preference == 'english':
        is_nepali = False
    else:
        is_nepali = has_devanagari(msg) or any(cue in msg_lower for cue in ROMAN_NEPALI_CUES)

    detected_language = 'nepali' if is_nepali else 'english'

    filters: Dict = {}
    intent = 'question'
    suggestions: List[str] = []

    # ── District map (English + Devanagari + Romanized) ──────────────────────
    district_map = {
        'kathmandu': 'Kathmandu', 'काठमाडौं': 'Kathmandu', 'ktm': 'Kathmandu', 'kahmandu': 'Kathmandu',
        'bhaktapur': 'Bhaktapur', 'भक्तपुर': 'Bhaktapur', 'bhaktpur': 'Bhaktapur',
        'lalitpur': 'Lalitpur', 'ललितपुर': 'Lalitpur', 'patan': 'Lalitpur',
        'pokhara': 'Pokhara', 'पोखरा': 'Pokhara',
        'chitwan': 'Chitwan', 'चितवन': 'Chitwan',
        'biratnagar': 'Biratnagar', 'विराटनगर': 'Biratnagar',
        'birgunj': 'Birgunj', 'बिरगंज': 'Birgunj',
        'dharan': 'Dharan', 'धरान': 'Dharan',
        'butwal': 'Butwal', 'बुटवल': 'Butwal',
        'hetauda': 'Hetauda', 'हेटौडा': 'Hetauda',
        'bharatpur': 'Bharatpur', 'भरतपुर': 'Bharatpur',
        'nepalgunj': 'Nepalgunj', 'नेपालगंज': 'Nepalgunj',
        'dhangadhi': 'Dhangadhi', 'धनगढी': 'Dhangadhi',
        'janakpur': 'Janakpur', 'जनकपुर': 'Janakpur',
    }
    for key, value in district_map.items():
        if key in msg_lower or key in msg:
            filters['district'] = value
            intent = 'search'
            break

    # ── Province map (English + Devanagari + Romanized) ───────────────────────
    province_map = {
        'koshi': 'Koshi', 'कोशी': 'Koshi', 'province 1': 'Koshi', 'प्रदेश १': 'Koshi',
        'madhesh': 'Madhesh', 'मधेश': 'Madhesh', 'province 2': 'Madhesh', 'प्रदेश २': 'Madhesh', 'madhes': 'Madhesh',
        'bagmati': 'Bagmati', 'बागमती': 'Bagmati', 'province 3': 'Bagmati', 'प्रदेश ३': 'Bagmati',
        'gandaki': 'Gandaki', 'गण्डकी': 'Gandaki', 'province 4': 'Gandaki', 'प्रदेश ४': 'Gandaki',
        'lumbini': 'Lumbini', 'लुम्बिनी': 'Lumbini', 'province 5': 'Lumbini', 'प्रदेश ५': 'Lumbini',
        'karnali': 'Karnali', 'कर्णाली': 'Karnali', 'province 6': 'Karnali', 'प्रदेश ६': 'Karnali',
        'sudurpashchim': 'Sudurpashchim', 'सुदूरपश्चिम': 'Sudurpashchim', 'province 7': 'Sudurpashchim', 'प्रदेश ७': 'Sudurpashchim', 'sudur paschim': 'Sudurpashchim',
    }
    for key, value in province_map.items():
        if key in msg_lower or key in msg:
            filters['province'] = value
            intent = 'search'
            break

    # ── Property type map ─────────────────────────────────────────────────────
    type_map = {
        'room': 'room', 'single room': 'room', 'kotha': 'room', 'कोठा': 'room', 'कोठाहरू': 'room',
        'flat': 'flat', 'फ्ल्याट': 'flat', 'fyat': 'flat',
        'apartment': 'apartment', 'अपार्टमेन्ट': 'apartment', 'apt': 'apartment',
        'house': 'house', 'ghar': 'house', 'घर': 'house', 'bungalow': 'house',
        'land': 'land', 'jagga': 'land', 'जग्गा': 'land', 'plot': 'land',
        'commercial': 'commercial', 'office': 'commercial', 'shop': 'commercial',
        'pasal': 'commercial', 'पसल': 'commercial', 'व्यावसायिक': 'commercial',
    }
    for keyword, ptype in type_map.items():
        if keyword.lower() in msg_lower or keyword in msg:
            filters['property_type'] = ptype
            intent = 'search'
            break

    # ── Price extraction ──────────────────────────────────────────────────────
    # Nepali number words → numeric value
    nepali_num_map = {
        'एक हजार': 1000, 'दुई हजार': 2000, 'तीन हजार': 3000, 'चार हजार': 4000,
        'पाँच हजार': 5000, 'छ हजार': 6000, 'सात हजार': 7000, 'आठ हजार': 8000,
        'नौ हजार': 9000, 'दश हजार': 10000, 'बाह्र हजार': 12000, 'पन्ध्र हजार': 15000,
        'बीस हजार': 20000, 'पच्चीस हजार': 25000, 'तीस हजार': 30000,
        'पचास हजार': 50000, 'एक लाख': 100000,
    }
    for word, value in nepali_num_map.items():
        if word in msg:
            filters['max_price'] = value
            intent = 'search'
            break

    if 'max_price' not in filters:
        price_patterns = [
            r'under\s*(?:rs\.?|npr\.?)?\s*(\d[\d,]*)',
            r'below\s*(?:rs\.?|npr\.?)?\s*(\d[\d,]*)',
            r'less\s*than\s*(?:rs\.?|npr\.?)?\s*(\d[\d,]*)',
            r'(\d[\d,]*)\s*(?:samma|सम्म|bhanda\s*kam|भन्दा\s*कम|muni|मुनि)',
            r'budget\s*(?:is|of)?\s*(?:rs\.?|npr\.?)?\s*(\d[\d,]*)',
            r'(?:rs\.?|npr\.?)\s*(\d[\d,]*)',
            r'(\d[\d,]*)\s*(?:rupee|rupees|rupe)',
        ]
        for pattern in price_patterns:
            m = re.search(pattern, msg_lower.replace(',', ''))
            if m:
                try:
                    filters['max_price'] = int(m.group(1).replace(',', ''))
                    intent = 'search'
                    break
                except ValueError:
                    continue

    # ── Purpose ───────────────────────────────────────────────────────────────
    purpose_map = {
        'family': 'family', 'families': 'family', 'pariwar': 'family', 'परिवार': 'family',
        'office': 'office', 'business': 'office', 'karyalaya': 'office', 'कार्यालय': 'office',
        'student': 'student', 'bachelor': 'student', 'bidhyarthi': 'student', 'विद्यार्थी': 'student',
    }
    for keyword, purpose in purpose_map.items():
        if keyword.lower() in msg_lower or keyword in msg:
            filters['rental_purpose'] = purpose
            intent = 'search'
            break

    # ── Room count ────────────────────────────────────────────────────────────
    room_match = re.search(r'(\d+)\s*(?:bhk|bedroom|room|bed|kotha|कोठा)', msg_lower)
    if room_match:
        try:
            filters['num_rooms'] = int(room_match.group(1))
            intent = 'search'
        except ValueError:
            filters.pop('num_rooms', None)

    # ── Ward number ───────────────────────────────────────────────────────────
    ward_match = re.search(r'ward\s*(?:no\.?|number)?\s*(\d+)', msg_lower)
    if not ward_match:
        ward_match = re.search(r'वार्ड\s*(\d+)', msg)
    if ward_match:
        filters['ward_number'] = ward_match.group(1)
        intent = 'search'

    # ── Build response ────────────────────────────────────────────────────────
    if filters:
        parts_en, parts_np = [], []
        if 'province' in filters:
            parts_en.append(f"in {filters['province']} Province")
            parts_np.append(f"{filters['province']} प्रदेशमा")
        if 'district' in filters:
            parts_en.append(f"in {filters['district']}")
            parts_np.append(f"{filters['district']}मा")
        if 'property_type' in filters:
            type_np = {'room': 'कोठा', 'flat': 'फ्ल्याट', 'house': 'घर',
                       'apartment': 'अपार्टमेन्ट', 'land': 'जग्गा', 'commercial': 'व्यावसायिक'}
            parts_en.append(f"({filters['property_type']})")
            parts_np.append(f"({type_np.get(filters['property_type'], filters['property_type'])})")
        if 'max_price' in filters:
            parts_en.append(f"under Rs. {filters['max_price']:,}")
            parts_np.append(f"Rs. {filters['max_price']:,} भन्दा कममा")
        if 'rental_purpose' in filters:
            purp_np = {'family': 'परिवारको लागि', 'student': 'विद्यार्थीको लागि', 'office': 'कार्यालयको लागि'}
            parts_en.append(f"for {filters['rental_purpose']}")
            parts_np.append(purp_np.get(filters['rental_purpose'], filters['rental_purpose']))
        if 'num_rooms' in filters:
            parts_en.append(f"with {filters['num_rooms']}+ rooms")
            parts_np.append(f"{filters['num_rooms']}+ कोठासहित")

        desc_en = ' '.join(parts_en) or 'matching your criteria'
        desc_np = ' '.join(parts_np) or 'तपाईंको मापदण्ड अनुसार'

        response = (
            f"हाम्रो डेटाबेसमा {desc_np} उपलब्ध सम्पत्तिहरू यहाँ छन्।"
            if is_nepali else
            f"Great! Here are the properties {desc_en} I found for you:"
        )
        suggestions = (
            ['अझ सस्तो खोज्नुहोस्', 'नक्सामा हेर्नुहोस्', 'फिल्टर थप्नुहोस्', 'मालिकलाई सम्पर्क गर्नुहोस्']
            if is_nepali else
            ['Show cheaper options', 'View on map', 'Refine filters', 'Contact owner']
        )

    else:
        # Special language-switch messages
        if any(w in msg_lower for w in ['nepali ma bolnus', 'nepali ma bola', 'talk in nepali', 'speak nepali']) \
                or 'नेपालीमा बोल्नुहोस्' in msg:
            intent = 'language_switch'
            response = "नमस्ते! म अब नेपालीमा बोल्छु। तपाईंलाई कस्तो सम्पत्ति चाहिन्छ? उदाहरण: 'काठमाडौंमा २०,००० भन्दा कमको फ्ल्याट देखाऊ'।"
            suggestions = ['काठमाडौंमा कोठा', 'ललितपुरमा फ्ल्याट', 'भक्तपुरमा घर', 'मद्दत']

        elif any(w in msg_lower for w in ['english ma bolnus', 'talk in english', 'switch to english', 'speak english']):
            intent = 'language_switch'
            response = "Sure! I'll respond in English from now on. How can I help you find a property today?"
            suggestions = ['Rooms in Kathmandu', 'Flats under 20000', 'Houses for family', 'Help']

        elif any(w in msg_lower for w in ['hello', 'hi', 'hey', 'good morning', 'good evening']) \
                or 'नमस्ते' in msg or 'namaste' in msg_lower or 'namaskar' in msg_lower:
            intent = 'greeting'
            if is_nepali:
                response = ("नमस्ते! 🙏 SPRS मा स्वागत छ – नेपालको स्मार्ट प्रोपर्टी भाडा प्रणाली!\n\n"
                            "म तपाईंको बिलेंगुअल रियल इस्टेट सहायक हुँ। मलाई बताउनुहोस्:\n"
                            "• 'काठमाडौंमा १५,००० भन्दा कमको कोठा देखाऊ'\n"
                            "• 'भक्तपुरमा परिवारको लागि घर खोज'\n"
                            "• 'ललितपुरमा फ्ल्याट चाहिन्छ'\n\n"
                            "तपाईंलाई के चाहिन्छ?")
            else:
                response = ("Namaste! 🙏 Welcome to SPRS – Nepal's Smart Property Rental System!\n\n"
                            "I'm your bilingual real estate assistant. Try asking:\n"
                            "• 'Find a flat in Kathmandu under Rs 25,000'\n"
                            "• 'Show rooms near Tribhuvan University'\n"
                            "• '2-bedroom house in Bhaktapur for family'\n\n"
                            "What kind of property are you looking for?")
            suggestions = (
                ['काठमाडौंमा कोठा', 'सस्तो फ्ल्याट', 'परिवारको घर', 'मद्दत']
                if is_nepali else
                ['Rooms in Kathmandu', 'Budget flats', 'Family houses', 'Help']
            )

        elif any(w in msg_lower for w in ['help', 'how to', 'what can', 'guide', 'kasari', 'maddat', 'मद्दत', 'कसरी']):
            intent = 'help'
            if is_nepali:
                response = ("म तपाईंलाई यसरी मद्दत गर्न सक्छु:\n\n"
                            "🏠 **सम्पत्ति खोज्नुहोस्** – जिल्ला, प्रकार, बजेट बताउनुहोस्\n"
                            "🗺️ **नक्सामा हेर्नुहोस्** – स्थान सहित सम्पत्ति हेर्नुहोस्\n"
                            "💬 **प्रश्न सोध्नुहोस्** – भाडा प्रक्रिया, क्षेत्र जानकारी\n\n"
                            "उदाहरण:\n"
                            "• 'भक्तपुरमा २०,००० भन्दा कमको फ्ल्याट'\n"
                            "• 'ललितपुरमा विद्यार्थीको लागि कोठा'\n"
                            "• 'पोखरामा व्यावसायिक ठाउँ'")
            else:
                response = ("Here's how I can help:\n\n"
                            "🏠 **Search Properties** – Tell me location, type, and budget\n"
                            "🗺️ **Map View** – See properties with directions\n"
                            "💬 **Ask Questions** – Rental process, area info, pricing\n\n"
                            "Examples:\n"
                            "• 'Flat in Bhaktapur under 20,000'\n"
                            "• 'Room for students in Lalitpur'\n"
                            "• 'Commercial space in Pokhara'")
            suggestions = (
                ['काठमाडौंमा कोठा खोज', 'नक्सा हेर्नुहोस्', 'सम्पत्ति ब्राउज गर्नुहोस्', 'मूल्य गाइड']
                if is_nepali else
                ['Search rooms', 'View map', 'Browse properties', 'Pricing guide']
            )

        elif any(w in msg_lower for w in ['thank', 'thanks', 'dhanyabad', 'dhanyavad', 'appreciate']) \
                or 'धन्यवाद' in msg:
            intent = 'thanks'
            response = (
                "धन्यवाद! 😊 अरू केही चाहिए भने मलाई भन्नुहोस्। शुभकामना!"
                if is_nepali else
                "You're welcome! 😊 Feel free to ask anytime. Happy house hunting! 🏠"
            )
            suggestions = (
                ['अरू सम्पत्ति खोज', 'मनपर्ने हेर्नुहोस्']
                if is_nepali else
                ['Search again', 'View favorites']
            )

        else:
            if is_nepali:
                response = ("म नेपालभरि भाडाको सम्पत्ति खोज्न सहयोग गर्न सक्छु। 🏠\n\n"
                            "उदाहरण:\n"
                            "• 'काठमाडौंमा १५,००० भन्दा कमको कोठा'\n"
                            "• 'भक्तपुरमा फ्ल्याट चाहिन्छ'\n"
                            "• 'ललितपुरमा परिवारको लागि २ कोठाको घर'")
            else:
                response = ("I can help you find rental properties across Nepal! 🏠\n\n"
                            "Try:\n"
                            "• 'Rooms in Kathmandu under Rs 15,000'\n"
                            "• 'Flat in Bhaktapur ward 5'\n"
                            "• '2-bedroom house for family in Lalitpur'")
            suggestions = (
                ['काठमाडौंमा कोठा', 'ललितपुरमा फ्ल्याट', 'परिवारको लागि घर', 'मद्दत']
                if is_nepali else
                ['Rooms in Kathmandu', 'Flats in Lalitpur', 'Family houses', 'Help']
            )

    return {
        'response': response,
        'filters': filters if filters else None,
        'intent': intent,
        'suggestions': suggestions,
        'detected_language': detected_language,
    }


def get_area_insights(district: str) -> Dict[str, Any]:
    """Get insights about a specific area."""
    properties = Property.objects.filter(
        district__icontains=district,
        status=Property.Status.AVAILABLE,
        is_approved=True
    )
    
    if not properties.exists():
        return {
            'found': False,
            'message': f"I don't have much data about {district} yet."
        }
    
    avg_price = properties.aggregate(avg=Avg('price'))['avg']
    total_count = properties.count()
    
    type_counts = {}
    for prop in properties:
        ptype = prop.get_property_type_display()
        type_counts[ptype] = type_counts.get(ptype, 0) + 1
    
    most_common = max(type_counts, key=type_counts.get) if type_counts else 'Properties'
    
    return {
        'found': True,
        'district': district,
        'average_price': round(avg_price, 0) if avg_price else 0,
        'total_properties': total_count,
        'most_common_type': most_common,
        'type_breakdown': type_counts
    }
