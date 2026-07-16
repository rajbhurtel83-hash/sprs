import random
import urllib.request
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from users.models import User
from properties.models import Property, PropertyImage, Amenity


# ---------------------------------------------------------------------------
# Unsplash image URLs (free, no-auth needed at low resolution)
# ---------------------------------------------------------------------------
UNSPLASH_URLS = [
    "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&q=80",
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&q=80",
    "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=800&q=80",
    "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800&q=80",
    "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?w=800&q=80",
    "https://images.unsplash.com/photo-1523217582562-09d0def993a6?w=800&q=80",
    "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&q=80",
    "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&q=80",
    "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&q=80",
    "https://images.unsplash.com/photo-1560185127-6ed189bf02f4?w=800&q=80",
    "https://images.unsplash.com/photo-1600585153490-76fb20a32601?w=800&q=80",
    "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?w=800&q=80",
    "https://images.unsplash.com/photo-1600573472592-401b489a3cdc?w=800&q=80",
    "https://images.unsplash.com/photo-1605276374104-dee2a0ed3cd6?w=800&q=80",
    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&q=80",
    "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=800&q=80",
    "https://images.unsplash.com/photo-1558036117-15d82a90b9b1?w=800&q=80",
    "https://images.unsplash.com/photo-1583608205776-bfd35f0d9f83?w=800&q=80",
    "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=800&q=80",
    "https://images.unsplash.com/photo-1576941089067-2de3c901e126?w=800&q=80",
    "https://images.unsplash.com/photo-1449844908441-8829872d2607?w=800&q=80",
    "https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=800&q=80",
    "https://images.unsplash.com/photo-1600047508006-aa1e44fa9010?w=800&q=80",
    "https://images.unsplash.com/photo-1600210492493-0946911123ea?w=800&q=80",
    "https://images.unsplash.com/photo-1600566752355-35792bedcfea?w=800&q=80",
]

# ---------------------------------------------------------------------------
# Amenities
# ---------------------------------------------------------------------------
AMENITIES_DATA = [
    {"name": "WiFi", "icon": "bi-wifi"},
    {"name": "Parking", "icon": "bi-car-front"},
    {"name": "Water Supply", "icon": "bi-droplet"},
    {"name": "Electricity", "icon": "bi-lightning"},
    {"name": "Balcony", "icon": "bi-building"},
    {"name": "Garden", "icon": "bi-tree"},
    {"name": "Security", "icon": "bi-shield-check"},
    {"name": "Nearby School", "icon": "bi-mortarboard"},
    {"name": "Nearby Hospital", "icon": "bi-hospital"},
    {"name": "Road Access", "icon": "bi-signpost"},
    {"name": "Kitchen", "icon": "bi-cup-hot"},
    {"name": "Attached Bathroom", "icon": "bi-droplet-half"},
    {"name": "Furnished", "icon": "bi-lamp"},
    {"name": "CCTV", "icon": "bi-camera-video"},
    {"name": "Earthquake Resistant", "icon": "bi-house-check"},
]

# ---------------------------------------------------------------------------
# Property data  (35 properties)
# ---------------------------------------------------------------------------
PROPERTIES_DATA = [
    # ── Kathmandu Metropolitan City ────────────────────────────────────────
    {
        "title": "Cozy Single Room in Kirtipur, Ward 1",
        "property_type": "room",
        "description": (
            "A well-maintained single room in the historic town of Kirtipur, "
            "perfect for students attending Tribhuvan University. The room has "
            "good ventilation and natural light. Walking distance to local "
            "markets and public transport stops."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "1",
        "address": "Kirtipur, near Tribhuvan University main gate",
        "price": 6000,
        "num_rooms": 1,
        "rental_purpose": "student",
        "latitude": 27.6783000,
        "longitude": 85.2783000,
    },
    {
        "title": "Modern 2BHK Flat in Balkhu, Ward 2",
        "property_type": "flat",
        "description": (
            "A spacious 2-bedroom flat located in the Balkhu area with easy "
            "access to the Ring Road. The flat features a modern kitchen, "
            "attached bathrooms, and a small balcony. Ideal for small families "
            "or working professionals commuting across the valley."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "2",
        "address": "Balkhu, opposite Nepal Electricity Authority",
        "price": 18000,
        "num_rooms": 2,
        "rental_purpose": "family",
        "latitude": 27.6883000,
        "longitude": 85.2983000,
    },
    {
        "title": "Studio Apartment in Kalimati, Ward 3",
        "property_type": "apartment",
        "description": (
            "A compact studio apartment in the bustling Kalimati area, just "
            "minutes from the famous Kalimati fruits and vegetable market. "
            "The unit comes with a built-in kitchenette and attached bathroom. "
            "Suitable for a single professional or a couple."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "3",
        "address": "Kalimati, near Kalimati Tarkari Bazaar",
        "price": 12000,
        "num_rooms": 1,
        "rental_purpose": "any",
        "latitude": 27.6983000,
        "longitude": 85.3033000,
    },
    {
        "title": "Office Space in Teku, Ward 4",
        "property_type": "commercial",
        "description": (
            "A ground-floor commercial space near the Teku area suitable for "
            "a startup office or retail shop. Located on a busy road with "
            "excellent visibility and foot traffic. Ample parking is available "
            "in the premises."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "4",
        "address": "Teku, near Teku Hospital",
        "price": 45000,
        "num_rooms": 2,
        "rental_purpose": "office",
        "latitude": 27.6983000,
        "longitude": 85.3133000,
    },
    {
        "title": "Furnished 1BHK in Tripureshwor, Ward 5",
        "property_type": "flat",
        "description": (
            "A fully furnished 1-bedroom flat in the Tripureshwor area close "
            "to the Tribhuvan University central campus and Bir Hospital. "
            "The flat includes a washing machine, refrigerator, and modular "
            "kitchen. Ideal for professionals posted in central Kathmandu."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "5",
        "address": "Tripureshwor, near Bir Hospital",
        "price": 20000,
        "num_rooms": 1,
        "rental_purpose": "any",
        "latitude": 27.6983000,
        "longitude": 85.3183000,
    },
    {
        "title": "Heritage House Near Basantapur, Ward 6",
        "property_type": "house",
        "description": (
            "A beautifully restored traditional Newari house near Basantapur "
            "Durbar Square. The house features carved wooden windows, a "
            "courtyard, and 4 bedrooms spread across three floors. Perfect "
            "for a family seeking a blend of culture and modern amenities."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "6",
        "address": "Basantapur, Asan Tole",
        "price": 55000,
        "num_rooms": 4,
        "rental_purpose": "family",
        "latitude": 27.7053000,
        "longitude": 85.3083000,
    },
    {
        "title": "Budget Room in Balaju, Ward 7",
        "property_type": "room",
        "description": (
            "An affordable single room in the Balaju industrial area with "
            "access to shared bathroom and kitchen. The room is close to "
            "Balaju Park and the Balaju bus stop. Best suited for students "
            "or daily-wage workers looking for budget accommodation."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "7",
        "address": "Balaju, near Balaju Industrial District",
        "price": 5000,
        "num_rooms": 1,
        "rental_purpose": "student",
        "latitude": 27.7233000,
        "longitude": 85.3033000,
    },
    {
        "title": "3BHK Apartment in Nayabazar, Ward 8",
        "property_type": "apartment",
        "description": (
            "A well-designed 3-bedroom apartment in the Nayabazar locale, "
            "minutes from Swayambhunath (Monkey Temple). The apartment "
            "offers panoramic views of the valley and comes with 24-hour "
            "water supply and dedicated parking."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "8",
        "address": "Nayabazar, near Swayambhunath road",
        "price": 32000,
        "num_rooms": 3,
        "rental_purpose": "family",
        "latitude": 27.7153000,
        "longitude": 85.3033000,
    },
    {
        "title": "Luxury Flat in Lazimpat, Ward 9",
        "property_type": "flat",
        "description": (
            "A premium fully-furnished flat in the prestigious Lazimpat "
            "neighborhood, surrounded by embassies and five-star hotels. "
            "The flat boasts marble flooring, a modular kitchen, and a "
            "spacious living area. Ideal for diplomats or corporate tenants."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "9",
        "address": "Lazimpat, near British Embassy",
        "price": 75000,
        "num_rooms": 3,
        "rental_purpose": "any",
        "latitude": 27.7213000,
        "longitude": 85.3233000,
    },
    {
        "title": "Modern 2BHK Apartment in Baneshwor, Ward 10",
        "property_type": "apartment",
        "description": (
            "A modern 2-bedroom apartment in the heart of New Baneshwor. "
            "The apartment features earthquake-resistant construction, CCTV "
            "security, and a rooftop terrace. Close to Everest Bank and "
            "multiple shopping centers on the Baneshwor-Koteshwor corridor."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "10",
        "address": "Baneshwor, near Everest Bank",
        "price": 25000,
        "num_rooms": 2,
        "rental_purpose": "family",
        "latitude": 27.6933000,
        "longitude": 85.3333000,
    },
    {
        "title": "Spacious Room in Maitidevi, Ward 11",
        "property_type": "room",
        "description": (
            "A bright and airy room in the Maitidevi area near Pashupatinath "
            "Temple. The room includes an attached bathroom and a small "
            "balcony. The neighborhood is peaceful yet well-connected to "
            "public transport routes heading towards Chabahil and Bouddha."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "11",
        "address": "Maitidevi, near Maitidevi Temple",
        "price": 8000,
        "num_rooms": 1,
        "rental_purpose": "student",
        "latitude": 27.7033000,
        "longitude": 85.3283000,
    },
    {
        "title": "Family House in Battisputali, Ward 12",
        "property_type": "house",
        "description": (
            "A 2-storey residential house in Battisputali with 5 bedrooms, "
            "a garden, and a garage. The property is located in a quiet "
            "residential lane close to Battisputali Chowk. Well-suited for "
            "a joint family or as a shared living arrangement."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "12",
        "address": "Battisputali, near Battisputali Chowk",
        "price": 60000,
        "num_rooms": 5,
        "rental_purpose": "family",
        "latitude": 27.7033000,
        "longitude": 85.3383000,
    },
    {
        "title": "2BHK Flat in Dhumbarahi, Ward 13",
        "property_type": "flat",
        "description": (
            "A neat 2-bedroom flat in Dhumbarahi on the second floor of a "
            "newly constructed building. The flat has cross-ventilation, "
            "modern bathroom fittings, and a separate utility area. Close "
            "to Dhumbarahi Chowk and multiple bus routes."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "13",
        "address": "Dhumbarahi, near Dhumbarahi Chowk",
        "price": 16000,
        "num_rooms": 2,
        "rental_purpose": "family",
        "latitude": 27.7183000,
        "longitude": 85.3283000,
    },
    {
        "title": "Premium Apartment in Maharajgunj, Ward 14",
        "property_type": "apartment",
        "description": (
            "A luxurious 3-bedroom apartment in Maharajgunj, one of "
            "Kathmandu's most sought-after residential areas. The apartment "
            "is near ICIMOD and UN offices. Features include an elevator, "
            "backup generator, and underground parking."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "14",
        "address": "Maharajgunj, near ICIMOD building",
        "price": 65000,
        "num_rooms": 3,
        "rental_purpose": "any",
        "latitude": 27.7363000,
        "longitude": 85.3353000,
    },
    {
        "title": "Student Room in Chabahil, Ward 15",
        "property_type": "room",
        "description": (
            "A budget-friendly room in Chabahil suitable for students or "
            "single tenants. The room is fully tiled and comes with a fan "
            "and a small cupboard. The area is well-connected to Bouddha, "
            "Baluwatar, and Mitrapark by local micro-bus services."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "15",
        "address": "Chabahil, near Chabahil Ganesh Temple",
        "price": 7000,
        "num_rooms": 1,
        "rental_purpose": "student",
        "latitude": 27.7143000,
        "longitude": 85.3433000,
    },
    {
        "title": "2BHK Near Bouddhanath Stupa, Ward 16",
        "property_type": "flat",
        "description": (
            "A charming 2-bedroom flat just a 5-minute walk from the "
            "Bouddhanath Stupa. The flat is on the top floor and offers "
            "spectacular views of the stupa and surrounding monasteries. "
            "Many cafes, restaurants, and Tibetan shops are within reach."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "16",
        "address": "Bouddha, near Bouddhanath Stupa main gate",
        "price": 22000,
        "num_rooms": 2,
        "rental_purpose": "any",
        "latitude": 27.7213000,
        "longitude": 85.3633000,
    },
    {
        "title": "Residential House in Jorpati, Ward 17",
        "property_type": "house",
        "description": (
            "A newly built residential house in Jorpati with 3 bedrooms, "
            "a kitchen garden, and a spacious terrace. Perfect for families "
            "seeking a quieter lifestyle away from the city core while "
            "remaining connected via the Jorpati-Sankhu road."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "17",
        "address": "Jorpati, near Kopan Monastery road",
        "price": 35000,
        "num_rooms": 3,
        "rental_purpose": "family",
        "latitude": 27.7303000,
        "longitude": 85.3733000,
    },
    {
        "title": "Land Plot in Gokarneshwor, Ward 18",
        "property_type": "land",
        "description": (
            "A rectangular land plot of 4 aana in Gokarneshwor with road "
            "access on two sides. The land is within the Kathmandu "
            "metropolitan boundary and suitable for residential construction "
            "or investment. Gokarna Forest Resort is nearby."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "18",
        "address": "Gokarneshwor, near Gokarna Forest Resort",
        "price": 200000,
        "num_rooms": 0,
        "rental_purpose": "any",
        "latitude": 27.7443000,
        "longitude": 85.3883000,
    },
    {
        "title": "Traditional Home in Sankhu, Ward 19",
        "property_type": "house",
        "description": (
            "A traditional Newari brick house in the ancient settlement of "
            "Sankhu, featuring original carvings and spacious rooms. The "
            "house has been retrofitted for earthquake resistance while "
            "preserving its cultural heritage. Close to Bajrayogini Temple."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "19",
        "address": "Sankhu, near Bajrayogini Temple road",
        "price": 28000,
        "num_rooms": 4,
        "rental_purpose": "family",
        "latitude": 27.7553000,
        "longitude": 85.4033000,
    },
    {
        "title": "1BHK Flat in Kageshwori, Ward 20",
        "property_type": "flat",
        "description": (
            "An affordable 1-bedroom flat in Kageshwori Manohara area. "
            "The flat is on the first floor with attached bathroom and a "
            "small kitchen. Located in a developing locality with good "
            "road connectivity to Bouddha and Jorpati."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "20",
        "address": "Kageshwori, near Manohara river bridge",
        "price": 10000,
        "num_rooms": 1,
        "rental_purpose": "any",
        "latitude": 27.7133000,
        "longitude": 85.3883000,
    },
    {
        "title": "3BHK Apartment in Koteshwor, Ward 22",
        "property_type": "apartment",
        "description": (
            "A modern 3-bedroom apartment in the Koteshwor area, one of "
            "Kathmandu's fastest-growing commercial hubs. The apartment "
            "features spacious rooms, a modular kitchen, and is close to "
            "the Koteshwor bus park and Ring Road intersection."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "22",
        "address": "Koteshwor, near Koteshwor Chowk",
        "price": 30000,
        "num_rooms": 3,
        "rental_purpose": "family",
        "latitude": 27.6783000,
        "longitude": 85.3433000,
    },
    {
        "title": "Commercial Shop in Thimi, Ward 23",
        "property_type": "commercial",
        "description": (
            "A well-positioned commercial shop space in Thimi on the "
            "Araniko Highway. The shop is on the ground floor with a "
            "shutter entrance, suitable for retail, electronics, or grocery "
            "business. High traffic area connecting Kathmandu to Bhaktapur."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "23",
        "address": "Thimi, Madhyapur, Araniko Highway",
        "price": 40000,
        "num_rooms": 1,
        "rental_purpose": "office",
        "latitude": 27.6783000,
        "longitude": 85.3833000,
    },
    {
        "title": "Family Flat in Satdobato, Ward 24",
        "property_type": "flat",
        "description": (
            "A comfortable 2-bedroom flat in Satdobato near the ICIMOD "
            "Knowledge Park. The flat has a well-designed layout with a "
            "separate dining space and a utility balcony. The neighborhood "
            "is family-friendly with several schools nearby."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "24",
        "address": "Satdobato, near Satdobato Chowk",
        "price": 17000,
        "num_rooms": 2,
        "rental_purpose": "family",
        "latitude": 27.6583000,
        "longitude": 85.3233000,
    },
    {
        "title": "2BHK Flat in Lagankhel, Ward 25",
        "property_type": "flat",
        "description": (
            "A centrally located 2-bedroom flat in Lagankhel, the commercial "
            "heart of Lalitpur. The flat is close to the Lagankhel bus park "
            "and Patan Dhoka. Grocery stores, banks, and hospitals are all "
            "within walking distance."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "25",
        "address": "Lagankhel, near Lagankhel Bus Park",
        "price": 19000,
        "num_rooms": 2,
        "rental_purpose": "any",
        "latitude": 27.6683000,
        "longitude": 85.3183000,
    },
    {
        "title": "Tourist Guest House in Thamel, Ward 26",
        "property_type": "house",
        "description": (
            "A 6-room guest house in the heart of Thamel, Kathmandu's "
            "world-famous tourist district. The property features a rooftop "
            "restaurant space and is surrounded by trekking gear shops, "
            "travel agencies, and nightlife. Excellent for hospitality use."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "26",
        "address": "Thamel, near Garden of Dreams",
        "price": 180000,
        "num_rooms": 6,
        "rental_purpose": "office",
        "latitude": 27.7153000,
        "longitude": 85.3123000,
    },
    {
        "title": "New Apartment in Kapan, Ward 27",
        "property_type": "apartment",
        "description": (
            "A brand-new 2-bedroom apartment in Kapan with modern amenities "
            "including a gym and rooftop garden. The building is earthquake "
            "resistant and has 24-hour security. Kapan offers a quieter "
            "lifestyle with easy access to the Ring Road."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "27",
        "address": "Kapan, near Kapan Monastery",
        "price": 23000,
        "num_rooms": 2,
        "rental_purpose": "family",
        "latitude": 27.7373000,
        "longitude": 85.3483000,
    },
    {
        "title": "Villa in Budhanilkantha, Ward 28",
        "property_type": "house",
        "description": (
            "An elegant villa-style house in Budhanilkantha with 4 bedrooms, "
            "a private garden, and a covered garage. The property is near the "
            "famous Budhanilkantha (Sleeping Vishnu) Temple. The Shivapuri "
            "Nagarjun National Park is a short hike away."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "28",
        "address": "Budhanilkantha, near Sleeping Vishnu Temple",
        "price": 90000,
        "num_rooms": 4,
        "rental_purpose": "family",
        "latitude": 27.7633000,
        "longitude": 85.3633000,
    },
    {
        "title": "Affordable Room in Tokha, Ward 29",
        "property_type": "room",
        "description": (
            "A clean and well-ventilated room in the Tokha area suitable "
            "for a working individual. The room is on the ground floor with "
            "a private entrance. Local shops and eateries are available in "
            "Tokha Bazaar, just a 5-minute walk away."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "29",
        "address": "Tokha, near Tokha Bazaar",
        "price": 5500,
        "num_rooms": 1,
        "rental_purpose": "any",
        "latitude": 27.7503000,
        "longitude": 85.2983000,
    },
    {
        "title": "2BHK House in Goldhunga, Ward 30",
        "property_type": "house",
        "description": (
            "A small 2-bedroom house in the quiet village of Goldhunga "
            "surrounded by greenery and terraced farmland. The house has "
            "a kitchen garden and unobstructed mountain views. Suitable "
            "for nature lovers who prefer a semi-rural lifestyle."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "30",
        "address": "Goldhunga, near Goldhunga Community School",
        "price": 14000,
        "num_rooms": 2,
        "rental_purpose": "family",
        "latitude": 27.7483000,
        "longitude": 85.2783000,
    },
    {
        "title": "Flat Near Nagarjun Forest, Ward 31",
        "property_type": "flat",
        "description": (
            "A peaceful 2-bedroom flat near the Nagarjun (Raniban) forest "
            "reserve. The flat has excellent air quality and views of the "
            "forested hills. It comes with covered parking and is ideal for "
            "families who value a green environment."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "31",
        "address": "Nagarjun, near Nagarjun Forest Reserve gate",
        "price": 15000,
        "num_rooms": 2,
        "rental_purpose": "family",
        "latitude": 27.7383000,
        "longitude": 85.2583000,
    },
    {
        "title": "Student Apartment in Raniban, Ward 32",
        "property_type": "apartment",
        "description": (
            "A purpose-built student apartment near Raniban with shared "
            "common areas, a study room, and high-speed WiFi. Each unit "
            "has its own attached bathroom. Several colleges and coaching "
            "centres are accessible via a short bus ride."
        ),
        "district": "Kathmandu",
        "municipality": "Kathmandu Metropolitan City",
        "ward_number": "32",
        "address": "Raniban, near Raniban Pipalbot",
        "price": 9000,
        "num_rooms": 1,
        "rental_purpose": "student",
        "latitude": 27.7283000,
        "longitude": 85.2683000,
    },

    # ── Lalitpur ───────────────────────────────────────────────────────────
    {
        "title": "Artistic Flat in Patan, Lalitpur Ward 5",
        "property_type": "flat",
        "description": (
            "A beautifully appointed 2-bedroom flat in historic Patan, "
            "within walking distance of Patan Durbar Square and the Patan "
            "Museum. The flat sits above a traditional Newari courtyard and "
            "is ideal for art lovers, researchers, or cultural enthusiasts."
        ),
        "district": "Lalitpur",
        "municipality": "Lalitpur Metropolitan City",
        "ward_number": "5",
        "address": "Patan, near Patan Durbar Square",
        "price": 22000,
        "num_rooms": 2,
        "rental_purpose": "any",
        "latitude": 27.6683000,
        "longitude": 85.3283000,
    },
    {
        "title": "Modern Apartment in Jhamsikhel, Lalitpur Ward 3",
        "property_type": "apartment",
        "description": (
            "A stylish 3-bedroom apartment in the upscale Jhamsikhel area "
            "of Lalitpur. The neighborhood is known for its trendy cafes, "
            "restaurants, and expatriate community. The apartment has lift "
            "access, CCTV security, and a children's play area."
        ),
        "district": "Lalitpur",
        "municipality": "Lalitpur Metropolitan City",
        "ward_number": "3",
        "address": "Jhamsikhel, near Jhamsikhel Chowk",
        "price": 45000,
        "num_rooms": 3,
        "rental_purpose": "family",
        "latitude": 27.6733000,
        "longitude": 85.3183000,
    },
    {
        "title": "Furnished Room in Kupondole, Lalitpur Ward 5",
        "property_type": "room",
        "description": (
            "A fully furnished room in the Kupondole area with an attached "
            "bathroom and a compact kitchen corner. The location offers easy "
            "access to both Patan and Kathmandu city centres via the Bagmati "
            "Bridge. Popular among IT professionals and students."
        ),
        "district": "Lalitpur",
        "municipality": "Lalitpur Metropolitan City",
        "ward_number": "5",
        "address": "Kupondole, near Kupondole Height",
        "price": 9000,
        "num_rooms": 1,
        "rental_purpose": "student",
        "latitude": 27.6883000,
        "longitude": 85.3183000,
    },
    {
        "title": "Executive Home in Jawalakhel, Lalitpur Ward 7",
        "property_type": "house",
        "description": (
            "A luxurious 4-bedroom house in Jawalakhel near the Jawalakhel "
            "Zoo and the United Nations office. The house features a private "
            "garden, solar-heated water, and a home-office room on the "
            "ground floor. Ideal for senior executives or diplomats."
        ),
        "district": "Lalitpur",
        "municipality": "Lalitpur Metropolitan City",
        "ward_number": "7",
        "address": "Jawalakhel, near Central Zoo entrance",
        "price": 110000,
        "num_rooms": 4,
        "rental_purpose": "family",
        "latitude": 27.6683000,
        "longitude": 85.3133000,
    },

    # ── Bhaktapur ──────────────────────────────────────────────────────────
    {
        "title": "Heritage Flat Near Bhaktapur Durbar Square, Ward 8",
        "property_type": "flat",
        "description": (
            "A tastefully renovated 2-bedroom flat overlooking the UNESCO "
            "World Heritage Bhaktapur Durbar Square. The flat retains "
            "traditional brickwork while offering modern plumbing and "
            "electrical fittings. Perfect for anyone who cherishes living "
            "history."
        ),
        "district": "Bhaktapur",
        "municipality": "Bhaktapur Municipality",
        "ward_number": "8",
        "address": "Bhaktapur Durbar Square area, Taumadhi Tole",
        "price": 18000,
        "num_rooms": 2,
        "rental_purpose": "any",
        "latitude": 27.6713000,
        "longitude": 85.4283000,
    },
    {
        "title": "Commercial Space in Kamalbinayak, Bhaktapur Ward 6",
        "property_type": "commercial",
        "description": (
            "A ground-floor commercial space at the busy Kamalbinayak "
            "intersection in Bhaktapur. The space is ideal for a pharmacy, "
            "stationery shop, or mobile repair store. The Arniko Highway "
            "ensures a steady flow of customers."
        ),
        "district": "Bhaktapur",
        "municipality": "Bhaktapur Municipality",
        "ward_number": "6",
        "address": "Kamalbinayak, near Kamalbinayak Temple",
        "price": 35000,
        "num_rooms": 1,
        "rental_purpose": "office",
        "latitude": 27.6783000,
        "longitude": 85.4183000,
    },
    {
        "title": "Peaceful House in Suryabinayak, Bhaktapur Ward 9",
        "property_type": "house",
        "description": (
            "A spacious 3-bedroom house in the serene Suryabinayak area on "
            "the outskirts of Bhaktapur. The house has a large courtyard, "
            "a rooftop terrace with mountain views, and is close to the "
            "Suryabinayak Temple. A great retreat from urban density."
        ),
        "district": "Bhaktapur",
        "municipality": "Suryabinayak Municipality",
        "ward_number": "9",
        "address": "Suryabinayak, near Suryabinayak Temple",
        "price": 25000,
        "num_rooms": 3,
        "rental_purpose": "family",
        "latitude": 27.6683000,
        "longitude": 85.4383000,
    },
]


class Command(BaseCommand):
    help = (
        "Seed the database with 35+ realistic Nepal rental properties "
        "across Kathmandu, Lalitpur, and Bhaktapur, including amenities "
        "and property images downloaded from Unsplash."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-images",
            action="store_true",
            help="Skip downloading images from Unsplash (faster, offline-safe).",
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _create_user(self):
        """Create or retrieve the property-owner user."""
        user, created = User.objects.get_or_create(
            username="user1",
            defaults={
                "email": "raaz@sprs.com",
                "first_name": "Raaz",
                "last_name": "Bhurtel",
                "role": "owner",
                "phone": "9841234567",
                "address": "Kathmandu, Nepal",
            },
        )
        if created:
            user.set_password("#Sprs12345")
            user.save()
            self.stdout.write(self.style.SUCCESS(
                "Created owner user: user1 / #Sprs12345"
            ))
        else:
            self.stdout.write("User 'user1' already exists -- skipping.")
        return user

    def _create_amenities(self):
        """Create all standard Nepal amenities and return a dict {name: obj}."""
        amenities = {}
        for item in AMENITIES_DATA:
            obj, created = Amenity.objects.get_or_create(
                name=item["name"],
                defaults={"icon": item["icon"]},
            )
            if not created:
                # Update icon if amenity already existed
                if obj.icon != item["icon"]:
                    obj.icon = item["icon"]
                    obj.save(update_fields=["icon"])
            amenities[obj.name] = obj
            status = "created" if created else "exists"
            self.stdout.write(f"  Amenity: {obj.name} ({obj.icon}) -- {status}")
        return amenities

    def _download_image(self, url, property_title, index):
        """Download an image from *url* and return a (filename, ContentFile)
        tuple, or ``None`` on failure."""
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            slug = property_title[:40].replace(" ", "_").lower()
            filename = f"{slug}_{index}.jpg"
            return filename, ContentFile(data)
        except Exception as exc:
            self.stderr.write(self.style.WARNING(
                f"    Could not download image: {exc}"
            ))
            return None

    # ------------------------------------------------------------------
    # main handler
    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        skip_images = options.get("no_images", False)

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n===  Seeding Nepal Properties  ===\n"
        ))

        # 1. User -------------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("Step 1: Owner user"))
        owner = self._create_user()

        # 2. Amenities ---------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("\nStep 2: Amenities"))
        amenities = self._create_amenities()
        amenity_names = list(amenities.keys())
        self.stdout.write(self.style.SUCCESS(
            f"  Total amenities: {len(amenities)}"
        ))

        # 3. Properties --------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("\nStep 3: Properties"))
        created_count = 0
        skipped_count = 0

        for idx, pdata in enumerate(PROPERTIES_DATA, start=1):
            title = pdata["title"]

            if Property.objects.filter(title=title, owner=owner).exists():
                self.stdout.write(f"  [{idx}] {title} -- already exists, skipping.")
                skipped_count += 1
                continue

            prop = Property.objects.create(
                owner=owner,
                title=title,
                property_type=pdata["property_type"],
                description=pdata["description"],
                district=pdata["district"],
                municipality=pdata["municipality"],
                ward_number=pdata["ward_number"],
                address=pdata["address"],
                price=pdata["price"],
                num_rooms=pdata["num_rooms"],
                rental_purpose=pdata["rental_purpose"],
                latitude=pdata["latitude"],
                longitude=pdata["longitude"],
                status="available",
                contact_phone="9841234567",
                contact_email="raaz@sprs.com",
                is_approved=True,
            )

            # Assign 3-7 random amenities
            num_amenities = random.randint(3, 7)
            chosen = random.sample(amenity_names, k=num_amenities)
            prop.amenities.set([amenities[n] for n in chosen])

            # Download 1-2 images per property
            if not skip_images:
                num_images = random.randint(1, 2)
                for img_i in range(num_images):
                    url = UNSPLASH_URLS[(idx + img_i) % len(UNSPLASH_URLS)]
                    result = self._download_image(url, title, img_i)
                    if result:
                        filename, content = result
                        pi = PropertyImage(
                            property=prop,
                            caption=f"{title} - Image {img_i + 1}",
                            is_primary=(img_i == 0),
                        )
                        pi.image.save(filename, content, save=True)
                        self.stdout.write(
                            f"    Saved image: {filename}"
                        )

            created_count += 1
            self.stdout.write(self.style.SUCCESS(
                f"  [{idx}] {title}  (Ward {pdata['ward_number']}, "
                f"{pdata['district']})  -- created"
            ))

        # 4. Summary -----------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("\n===  Summary  ==="))
        self.stdout.write(f"  Owner user   : user1 (Raaz Bhurtel)")
        self.stdout.write(f"  Amenities    : {len(amenities)}")
        self.stdout.write(f"  Properties   : {created_count} created, {skipped_count} skipped")
        self.stdout.write(f"  Total in DB  : {Property.objects.count()}")
        if skip_images:
            self.stdout.write("  Images       : skipped (--no-images flag)")
        else:
            self.stdout.write(
                f"  Images       : {PropertyImage.objects.filter(property__owner=owner).count()}"
            )
        self.stdout.write(self.style.SUCCESS("\nDone! Database seeded successfully.\n"))
