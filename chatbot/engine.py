import json
import re
from django.conf import settings

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from properties.models import Property, Amenity


SYSTEM_PROMPT = """You are SPRS Assistant, an intelligent chatbot for the Smart Property Rental System in Nepal.
You help users find rental properties, understand the platform, and answer questions.

**MULTILINGUAL SUPPORT:**
You can communicate in both English and Nepali (नेपाली) languages.
- If the user writes in Nepali or asks to speak in Nepali, respond in Nepali.
- If the user writes in English, respond in English.
- Understand Romanized Nepali (e.g., "kotha" = room, "ghar" = house, "bhada" = rent)

Common Nepali terms:
- कोठा/kotha = Room
- फ्ल्याट/flat = Flat  
- घर/ghar = House
- भाडा/bhada = Rent
- कति पर्छ?/kati parcha? = How much?
- मलाई...चाहिन्छ/malai...chahincha = I need...

When a user asks to find properties, extract search filters from their message and return them as JSON.
Return your response in this exact format:
{"response": "your friendly message here (in user's language)", "filters": {"key": "value"}}

Available filter keys:
- district: string (e.g., "Kathmandu", "Bhaktapur", "Lalitpur")
- municipality: string
- ward_number: string
- property_type: one of "room", "flat", "apartment", "house", "land", "commercial"
- max_price: number
- min_price: number
- num_rooms: number
- rental_purpose: one of "family", "office", "student", "any"
- amenities: list of strings

If the user is NOT searching for properties (e.g., asking about how to use the system, general questions), return:
{"response": "your helpful answer here", "filters": null}

Always be friendly, helpful, and knowledgeable about Nepal's rental market.
Currency is Nepali Rupees (NPR/Rs.) - नेपाली रुपैयाँ.
Common districts: Kathmandu (काठमाडौं), Bhaktapur (भक्तपुर), Lalitpur (ललितपुर), Pokhara (पोखरा), Chitwan (चितवन), etc.
"""


def get_chatbot_response(user_message, conversation_history=None):
    """Get AI response from OpenAI API and extract property filters."""
    api_key = getattr(settings, 'OPENAI_API_KEY', None)

    if not api_key or not OpenAI:
        return _fallback_response(user_message)

    client = OpenAI(api_key=api_key)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if conversation_history:
        for msg in conversation_history[-10:]:
            messages.append(msg)

    messages.append({"role": "user", "content": user_message})

    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )

        raw = completion.choices[0].message.content.strip()
        return _parse_response(raw)

    except Exception as e:
        return _fallback_response(user_message)


def _parse_response(raw_text):
    """Parse the AI response to extract message and filters."""
    try:
        data = json.loads(raw_text)
        return {
            'response': data.get('response', raw_text),
            'filters': data.get('filters'),
        }
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return {
                    'response': data.get('response', raw_text),
                    'filters': data.get('filters'),
                }
            except json.JSONDecodeError:
                pass
        return {'response': raw_text, 'filters': None}


def search_properties_with_filters(filters):
    """Search properties using extracted filters."""
    if not filters:
        return []

    qs = Property.objects.filter(
        status=Property.Status.AVAILABLE,
        is_approved=True,
    ).select_related('owner').prefetch_related('images')

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
        for amenity_name in filters['amenities']:
            qs = qs.filter(amenities__name__icontains=amenity_name)

    return qs[:10]


def _fallback_response(user_message):
    """Provide a basic response when OpenAI API is unavailable. Supports English and Nepali."""
    msg_lower = user_message.lower()
    
    # Detect if user wants Nepali
    is_nepali = any(word in msg_lower for word in [
        'nepali', 'नेपाली', 'nepali ma', 'नेपालीमा', 'bolnus', 'बोल्नुहोस्'
    ])

    filters = {}

    # Districts - both English and Nepali/Romanized
    districts = {
        'kathmandu': 'Kathmandu', 'काठमाडौं': 'Kathmandu', 'ktm': 'Kathmandu',
        'bhaktapur': 'Bhaktapur', 'भक्तपुर': 'Bhaktapur',
        'lalitpur': 'Lalitpur', 'ललितपुर': 'Lalitpur', 'patan': 'Lalitpur',
        'pokhara': 'Pokhara', 'पोखरा': 'Pokhara',
        'chitwan': 'Chitwan', 'चितवन': 'Chitwan',
        'biratnagar': 'Biratnagar', 'विराटनगर': 'Biratnagar',
        'birgunj': 'Birgunj', 'बिरगंज': 'Birgunj',
        'dharan': 'Dharan', 'धरान': 'Dharan',
        'butwal': 'Butwal', 'बुटवल': 'Butwal',
        'hetauda': 'Hetauda', 'हेटौडा': 'Hetauda'
    }
    for key, value in districts.items():
        if key in msg_lower:
            filters['district'] = value
            break

    # Property types - both English and Nepali/Romanized
    types = {
        'room': 'room', 'kotha': 'room', 'कोठा': 'room',
        'flat': 'flat', 'फ्ल्याट': 'flat',
        'apartment': 'apartment', 'अपार्टमेन्ट': 'apartment',
        'house': 'house', 'ghar': 'house', 'घर': 'house',
        'land': 'land', 'jagga': 'land', 'जग्गा': 'land',
        'commercial': 'commercial', 'office space': 'commercial', 'shop': 'commercial',
        'pasal': 'commercial', 'पसल': 'commercial'
    }
    for keyword, ptype in types.items():
        if keyword in msg_lower:
            filters['property_type'] = ptype
            break

    # Price patterns - both English and Nepali
    price_patterns = [
        r'under\s+(\d+)', r'below\s+(\d+)', r'less\s+than\s+(\d+)',
        r'budget\s+(\d+)', r'(\d+)\s*samma', r'(\d+)\s*सम्म',
        r'(\d+)\s*bhanda\s*kam', r'(\d+)\s*भन्दा\s*कम'
    ]
    for pattern in price_patterns:
        price_match = re.search(pattern, msg_lower)
        if price_match:
            filters['max_price'] = int(price_match.group(1))
            break

    # Purposes - both English and Nepali
    purposes = {
        'family': 'family', 'pariwar': 'family', 'परिवार': 'family',
        'office': 'office', 'karyalaya': 'office', 'कार्यालय': 'office',
        'student': 'student', 'bidhyarthi': 'student', 'विद्यार्थी': 'student'
    }
    for keyword, purpose in purposes.items():
        if keyword in msg_lower:
            filters['rental_purpose'] = purpose
            break

    # Ward number
    ward_match = re.search(r'ward\s+(\d+)', msg_lower)
    if ward_match:
        filters['ward_number'] = ward_match.group(1)

    # Room count
    rooms_match = re.search(r'(\d+)\s*(?:room|bhk|bedroom|kotha|कोठा)', msg_lower)
    if rooms_match:
        filters['num_rooms'] = int(rooms_match.group(1))

    if filters:
        parts = []
        if 'district' in filters:
            parts.append(f"in {filters['district']}")
        if 'property_type' in filters:
            parts.append(f"({filters['property_type']})")
        if 'max_price' in filters:
            parts.append(f"under Rs. {filters['max_price']:,}")
        if 'rental_purpose' in filters:
            parts.append(f"for {filters['rental_purpose']}")
        desc = ' '.join(parts)
        
        if is_nepali:
            response = f"तपाईंको खोजी अनुसार {desc} मा प्रोपर्टीहरू फेला परे। यहाँ परिणामहरू छन्:"
        else:
            response = f"I found properties matching your search {desc}. Here are the results:"
    else:
        # Greetings
        if any(w in msg_lower for w in ['hello', 'hi', 'namaste', 'नमस्ते', 'hey', 'namaskar', 'नमस्कार']):
            if is_nepali or any(w in msg_lower for w in ['namaste', 'नमस्ते', 'namaskar', 'नमस्कार']):
                response = "नमस्ते! SPRS मा स्वागत छ। म तपाईंलाई नेपालभरि भाडाको प्रोपर्टी खोज्न मद्दत गर्न सक्छु। मलाई 'काठमाडौंमा कोठा चाहिन्छ' वा 'ललितपुरमा फ्ल्याट खोज्नुहोस्' जस्तो भन्नुहोस्।"
            else:
                response = "Namaste! Welcome to SPRS. I can help you find rental properties across Nepal. Try asking me something like 'Find a room in Kathmandu under 15000' or 'Show flats in Bhaktapur'."
        # Help
        elif any(w in msg_lower for w in ['help', 'how', 'what can', 'maddat', 'मद्दत', 'kasari', 'कसरी']):
            if is_nepali:
                response = "म तपाईंलाई प्रोपर्टी खोज्न मद्दत गर्न सक्छु! यसरी प्रयास गर्नुहोस्:\n- 'काठमाडौंमा १५००० मुनि कोठा खोज्नुहोस्'\n- 'भक्तपुर वार्ड ५ मा फ्ल्याट'\n- 'ललितपुरमा परिवारको लागि घर'\n\nतपाईं प्रोपर्टी ब्राउज, मनपर्ने सेभ, र मालिकलाई सन्देश पनि पठाउन सक्नुहुन्छ।"
            else:
                response = "I can help you search for properties! Try:\n- 'Find a room in Kathmandu under 15000'\n- 'Show flats in Bhaktapur ward 5'\n- 'I need a house for family in Lalitpur'\n- 'Commercial space in Pokhara'\n\nYou can also browse properties, save favorites, and message property owners directly."
        # Thanks
        elif any(w in msg_lower for w in ['thank', 'thanks', 'dhanyabad', 'धन्यवाद']):
            if is_nepali or any(w in msg_lower for w in ['dhanyabad', 'धन्यवाद']):
                response = "धन्यवाद! अरू केही चाहिए भने भन्नुहोस्। शुभकामना!"
            else:
                response = "You're welcome! Let me know if you need anything else. Happy house hunting!"
        # Language switch request
        elif is_nepali:
            response = "नमस्ते! म अब नेपालीमा बोल्छु। तपाईंलाई कस्तो प्रोपर्टी चाहिन्छ? उदाहरणको लागि: 'काठमाडौंमा कोठा चाहिन्छ' वा 'ललितपुरमा फ्ल्याट खोज्नुहोस्'।"
        else:
            response = "I can help you find rental properties in Nepal. Try telling me what you're looking for, for example: 'Find a 2-room flat in Kathmandu under 20000 for family'."

    return {
        'response': response,
        'filters': filters if filters else None,
    }
