"""
seed_all_nepal.py
=================
Populate SPRS with demo properties in EVERY ward of EVERY municipality
of EVERY district in Nepal (77 districts, 753 municipalities, ~6,000+ wards).

Usage:
    python manage.py seed_all_nepal                       # Full seed with images
    python manage.py seed_all_nepal --no-images           # Skip image downloads
    python manage.py seed_all_nepal --province Koshi      # Seed one province only
    python manage.py seed_all_nepal --district Kathmandu  # Seed one district only
    python manage.py seed_all_nepal --clear               # Remove existing first
    python manage.py seed_all_nepal --images-per-property 5  # Fewer images
"""

import hashlib
import math
import os
import random
import time
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from properties.models import Amenity, Property, PropertyImage
from users.management.commands.nepal_data import DISTRICTS
from users.models import User

# ═══════════════════════════════════════════════════════════════════════════
# IMAGE POOL  (strictly categorized by property type)
# Each property draws images ONLY from its own type pool.
# House → house photos, Land → land photos, Room → room photos, etc.
# Images are downloaded once to a local cache and reused.
# ═══════════════════════════════════════════════════════════════════════════
IMAGE_POOL = {
    # House - exterior house photos only
    "house": [
        "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&q=80",
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&q=80",
        "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=800&q=80",
        "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800&q=80",
        "https://images.unsplash.com/photo-1583608205776-bfd35f0d9f83?w=800&q=80",
        "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=800&q=80",
        "https://images.unsplash.com/photo-1576941089067-2de3c901e126?w=800&q=80",
        "https://images.unsplash.com/photo-1449844908441-8829872d2607?w=800&q=80",
        "https://images.unsplash.com/photo-1605276374104-dee2a0ed3cd6?w=800&q=80",
        "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?w=800&q=80",
    ],
    # Apartment - apartment building & interior photos
    "apartment": [
        "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800&q=80",
        "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&q=80",
        "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&q=80",
        "https://images.unsplash.com/photo-1560185127-6ed189bf02f4?w=800&q=80",
        "https://images.unsplash.com/photo-1600585153490-76fb20a32601?w=800&q=80",
        "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?w=800&q=80",
        "https://images.unsplash.com/photo-1600573472592-401b489a3cdc?w=800&q=80",
        "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&q=80",
        "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=800&q=80",
        "https://images.unsplash.com/photo-1558036117-15d82a90b9b1?w=800&q=80",
    ],
    # Room - bedroom & single room photos
    "room": [
        "https://images.unsplash.com/photo-1540518614846-7eded433c457?w=800&q=80",
        "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=800&q=80",
        "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=800&q=80",
        "https://images.unsplash.com/photo-1616594039964-ae9021a400a0?w=800&q=80",
        "https://images.unsplash.com/photo-1617325247661-675ab4b64ae2?w=800&q=80",
        "https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=800&q=80",
        "https://images.unsplash.com/photo-1631679706909-1844bbd07221?w=800&q=80",
        "https://images.unsplash.com/photo-1616137466211-f736a1e16bb4?w=800&q=80",
        "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&q=80",
        "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=800&q=80",
    ],
    # Land - open land, plots, terrain photos
    "land": [
        "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800&q=80",
        "https://images.unsplash.com/photo-1628624747186-a941c476b7ef?w=800&q=80",
        "https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=800&q=80",
        "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=800&q=80",
        "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80",
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=800&q=80",
        "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80",
        "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80",
        "https://images.unsplash.com/photo-1595880500386-4b33823b29cd?w=800&q=80",
        "https://images.unsplash.com/photo-1500076656116-558758c991c1?w=800&q=80",
    ],
    # Commercial - office, shop, commercial space photos
    "commercial": [
        "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&q=80",
        "https://images.unsplash.com/photo-1497366811353-6870744d04b2?w=800&q=80",
        "https://images.unsplash.com/photo-1604328698692-f76ea9498e76?w=800&q=80",
        "https://images.unsplash.com/photo-1556761175-4b46a572b786?w=800&q=80",
        "https://images.unsplash.com/photo-1497215842964-222b430dc094?w=800&q=80",
        "https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=800&q=80",
        "https://images.unsplash.com/photo-1568992687947-868a62a9f521?w=800&q=80",
        "https://images.unsplash.com/photo-1600508774634-4e11d34730e2?w=800&q=80",
        "https://images.unsplash.com/photo-1577412647305-991150c7d163?w=800&q=80",
        "https://images.unsplash.com/photo-1582037928769-181f2644ecb7?w=800&q=80",
    ],
    # Flat - flat/apartment interior photos
    "flat": [
        "https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=800&q=80",
        "https://images.unsplash.com/photo-1600047508006-aa1e44fa9010?w=800&q=80",
        "https://images.unsplash.com/photo-1600210492493-0946911123ea?w=800&q=80",
        "https://images.unsplash.com/photo-1600566752355-35792bedcfea?w=800&q=80",
        "https://images.unsplash.com/photo-1523217582562-09d0def993a6?w=800&q=80",
        "https://images.unsplash.com/photo-1600585153490-76fb20a32601?w=800&q=80",
        "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?w=800&q=80",
        "https://images.unsplash.com/photo-1600573472592-401b489a3cdc?w=800&q=80",
        "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&q=80",
        "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=800&q=80",
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
# AMENITIES
# ═══════════════════════════════════════════════════════════════════════════
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

# ═══════════════════════════════════════════════════════════════════════════
# PROPERTY GENERATION PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════

# Property types cycle per ward - urban areas get more variety
PROP_TYPES_URBAN = ["house", "flat", "apartment", "room", "commercial", "land"]
PROP_TYPES_SEMI = ["house", "flat", "apartment", "room", "land", "commercial"]
PROP_TYPES_RURAL = ["house", "room", "land", "flat", "house", "room"]

# Price ranges (NRs) by (property_type, zone)
PRICE_RANGES = {
    ("room", "terai"): (3000, 10000),
    ("room", "hill"): (4000, 12000),
    ("room", "mountain"): (3000, 8000),
    ("flat", "terai"): (10000, 35000),
    ("flat", "hill"): (12000, 45000),
    ("flat", "mountain"): (8000, 25000),
    ("apartment", "terai"): (15000, 50000),
    ("apartment", "hill"): (18000, 75000),
    ("apartment", "mountain"): (12000, 35000),
    ("house", "terai"): (15000, 80000),
    ("house", "hill"): (20000, 120000),
    ("house", "mountain"): (12000, 60000),
    ("land", "terai"): (50000, 500000),
    ("land", "hill"): (80000, 800000),
    ("land", "mountain"): (30000, 300000),
    ("commercial", "terai"): (20000, 100000),
    ("commercial", "hill"): (25000, 150000),
    ("commercial", "mountain"): (15000, 60000),
}

ROOMS_RANGE = {
    "room": (1, 1), "flat": (1, 3), "apartment": (2, 4),
    "house": (2, 6), "land": (0, 0), "commercial": (1, 4),
}

RENTAL_PURPOSES = {
    "room": ["student", "any"],
    "flat": ["family", "any"],
    "apartment": ["family", "any", "office"],
    "house": ["family", "office"],
    "land": ["any"],
    "commercial": ["office"],
}

# Amenities profiles per property type
AMENITY_PROFILES = {
    "room": {
        "always": ["Electricity", "Water Supply"],
        "likely": ["WiFi", "Attached Bathroom", "Road Access"],
        "sometimes": ["Kitchen", "Parking", "Nearby School"],
    },
    "flat": {
        "always": ["Electricity", "Water Supply", "Kitchen", "Attached Bathroom"],
        "likely": ["WiFi", "Balcony", "Road Access", "Parking"],
        "sometimes": ["Security", "CCTV", "Furnished", "Nearby School"],
    },
    "apartment": {
        "always": ["Electricity", "Water Supply", "Kitchen", "Attached Bathroom", "Parking"],
        "likely": ["WiFi", "Balcony", "Security", "CCTV", "Road Access"],
        "sometimes": ["Garden", "Furnished", "Earthquake Resistant", "Nearby Hospital"],
    },
    "house": {
        "always": ["Electricity", "Water Supply", "Kitchen", "Attached Bathroom", "Road Access"],
        "likely": ["Parking", "Garden", "Balcony", "WiFi"],
        "sometimes": ["Security", "CCTV", "Furnished", "Earthquake Resistant",
                       "Nearby School", "Nearby Hospital"],
    },
    "land": {
        "always": ["Road Access"],
        "likely": ["Electricity", "Water Supply"],
        "sometimes": ["Nearby School", "Nearby Hospital"],
    },
    "commercial": {
        "always": ["Electricity", "Water Supply", "Road Access", "Parking"],
        "likely": ["WiFi", "Security", "CCTV", "Attached Bathroom"],
        "sometimes": ["Furnished", "Earthquake Resistant"],
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# DESCRIPTION TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════
ADJECTIVES = [
    "Cozy", "Spacious", "Modern", "Well-maintained", "Bright", "Charming",
    "Comfortable", "Newly-built", "Renovated", "Premium", "Affordable",
    "Elegant", "Sunny", "Quiet", "Beautiful", "Well-furnished",
]

ZONE_EXTRAS = {
    "terai": [
        "The flat Terai terrain makes commuting easy.",
        "Near the East-West Highway with excellent connectivity.",
        "The area has a warm climate and fertile surroundings.",
        "Local markets and healthcare facilities are nearby.",
        "Well-connected to border towns and regional centres.",
    ],
    "hill": [
        "Enjoy pleasant hill climate with cool breezes.",
        "The area offers scenic views of the surrounding hills.",
        "Terraced landscapes and green valleys surround the property.",
        "The neighborhood has a rich cultural heritage.",
        "Local temples and community centres add charm to the area.",
    ],
    "mountain": [
        "Breathtaking mountain views are visible from the property.",
        "The area is known for its pristine natural beauty.",
        "A gateway to popular trekking routes and national parks.",
        "The crisp mountain air and peaceful environment are unmatched.",
        "Traditional mountain architecture blends with modern facilities.",
    ],
}

DESC_TEMPLATES = {
    "room": [
        "A well-maintained {adj} room in {muni_full}, Ward {ward} of {district} district. "
        "The room features good ventilation and natural light. {extra} "
        "Walking distance to local markets and public transport. "
        "Ideal for students or working professionals seeking affordable accommodation.",

        "An affordable single room located in Ward {ward}, {muni_full}, {district}. "
        "The room comes with an attached bathroom and a small balcony. "
        "{extra} "
        "The neighborhood offers easy access to daily necessities and local bus services.",

        "A budget-friendly room available in {muni_full}, {district} district. "
        "Situated in Ward {ward}, this {adj} room is suitable for a single tenant. "
        "{extra} "
        "Basic amenities including water supply and electricity are available.",
    ],
    "flat": [
        "A spacious {rooms}BHK flat in {muni_full}, Ward {ward}, {district} district. "
        "The flat features a modern kitchen, attached bathrooms, and a balcony. "
        "{extra} "
        "Ideal for families looking for comfortable living in the area.",

        "A well-designed {rooms}-bedroom flat located in Ward {ward} of {muni_full}, {district}. "
        "The flat offers cross-ventilation and is situated in a {adj} neighborhood. "
        "{extra} "
        "Close to schools, hospitals, and major road connections.",

        "An attractive {rooms}BHK flat available in {muni_full}, Ward {ward}, {district}. "
        "This {adj} flat comes with tiled flooring and modular kitchen fittings. "
        "{extra} "
        "Perfect for families or professionals seeking a quality residence.",
    ],
    "apartment": [
        "A modern {rooms}-bedroom apartment in {muni_full}, Ward {ward}, {district} district. "
        "The apartment features earthquake-resistant construction and CCTV security. "
        "{extra} "
        "Located in a prime area with easy access to markets and public transport.",

        "A premium {rooms}BHK apartment in Ward {ward}, {muni_full}, {district}. "
        "This {adj} apartment offers elevator access with dedicated parking. "
        "{extra} "
        "An excellent choice for families seeking a secure and comfortable home.",

        "A newly constructed {rooms}-bedroom apartment in {muni_full}, {district} district. "
        "Situated in Ward {ward}, this apartment boasts panoramic views and modern fittings. "
        "{extra} "
        "The building has 24-hour water supply and backup generator.",
    ],
    "house": [
        "A {adj} {rooms}-bedroom house in {muni_full}, Ward {ward}, {district} district. "
        "The house features a private garden and spacious terrace. "
        "{extra} "
        "Perfect for families looking for a spacious home in the region.",

        "A well-built residential house in Ward {ward}, {muni_full}, {district}. "
        "This {rooms}-bedroom house comes with a courtyard and kitchen garden. "
        "{extra} "
        "The neighborhood is peaceful and well-connected to main roads.",

        "A beautiful {rooms}-bedroom house in {muni_full}, {district} district. "
        "Located in Ward {ward}, the property offers multiple floors and rooftop views. "
        "{extra} "
        "Suitable for a family seeking quality living in {district}.",
    ],
    "land": [
        "A prime land plot in {muni_full}, Ward {ward}, {district} district. "
        "The plot has road access and is suitable for residential construction. "
        "{extra} "
        "Located in an area with growing development potential.",

        "A rectangular land plot in Ward {ward}, {muni_full}, {district}. "
        "The land offers clear titles and proximity to main roads. "
        "{extra} "
        "An excellent investment opportunity in {district} district.",

        "A well-located land parcel in {muni_full}, {district} district, Ward {ward}. "
        "This {adj} plot is ideal for construction or investment purposes. "
        "{extra} "
        "Surrounded by developing infrastructure with good road connectivity.",
    ],
    "commercial": [
        "A {adj} commercial space in {muni_full}, Ward {ward}, {district} district. "
        "The space is on the ground floor with high visibility. "
        "{extra} "
        "Located in a high-traffic area, ideal for retail or office use.",

        "A well-positioned commercial property in Ward {ward}, {muni_full}, {district}. "
        "This {adj} space features a shutter entrance with ample parking. "
        "{extra} "
        "Perfect for a startup, retail shop, or professional office.",

        "A ground-floor commercial space in {muni_full}, {district} district. "
        "Situated in Ward {ward}, this property is in a bustling market area. "
        "{extra} "
        "Excellent visibility and footfall for business operations.",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _ward_coords(district_lat, district_lng, muni_idx, muni_count, ward, ward_count):
    """Generate GPS coordinates for a ward within a municipality."""
    spread = 0.12
    angle = (2 * math.pi * muni_idx) / max(muni_count, 1)
    r = spread * (0.3 + 0.7 * (muni_idx % 3) / 3)
    muni_lat = district_lat + r * math.sin(angle)
    muni_lng = district_lng + r * math.cos(angle)

    ward_spread = 0.025
    ward_angle = (2 * math.pi * (ward - 1)) / max(ward_count, 1)
    wr = ward_spread * (0.4 + 0.6 * ((ward * 7) % 5) / 5)
    lat = muni_lat + wr * math.sin(ward_angle)
    lng = muni_lng + wr * math.cos(ward_angle)

    lat = max(26.35, min(30.45, lat))
    lng = max(80.06, min(88.20, lng))
    return round(lat, 7), round(lng, 7)


def _make_title(prop_type, muni_name, ward, rooms, district):
    """Generate a readable property title."""
    labels = {
        "room": "Room", "flat": f"{rooms}BHK Flat",
        "apartment": f"{rooms}BHK Apartment", "house": f"{rooms}-Bedroom House",
        "land": "Land Plot", "commercial": "Commercial Space",
    }
    return f"{labels.get(prop_type, 'Property')} in {muni_name}, {district} - Ward {ward}"


def _make_description(prop_type, district, muni_name, muni_type, ward, zone, rooms):
    """Generate a realistic property description."""
    type_labels = {
        "MC": "Metropolitan City", "SMC": "Sub-Metropolitan City",
        "M": "Municipality", "RM": "Rural Municipality",
    }
    muni_full = f"{muni_name} {type_labels.get(muni_type, 'Municipality')}"

    seed = hashlib.md5(f"{district}-{muni_name}-{ward}-{prop_type}".encode()).hexdigest()
    rng = random.Random(seed)

    templates = DESC_TEMPLATES.get(prop_type, DESC_TEMPLATES["room"])
    template = rng.choice(templates)

    return template.format(
        adj=rng.choice(ADJECTIVES),
        rooms=rooms,
        muni_full=muni_full,
        ward=ward,
        district=district,
        extra=rng.choice(ZONE_EXTRAS.get(zone, ZONE_EXTRAS["hill"])),
    )


def _select_amenities(prop_type, amenities_dict, rng):
    """Pick amenities appropriate for the property type."""
    profile = AMENITY_PROFILES.get(prop_type, AMENITY_PROFILES["room"])
    selected = set()
    for name in profile["always"]:
        if name in amenities_dict:
            selected.add(name)
    for name in profile["likely"]:
        if name in amenities_dict and rng.random() < 0.7:
            selected.add(name)
    for name in profile["sometimes"]:
        if name in amenities_dict and rng.random() < 0.3:
            selected.add(name)
    return [amenities_dict[n] for n in selected if n in amenities_dict]


def _get_image_urls(prop_type, prop_index):
    """Return image URLs for a property — ONLY from the matching type pool."""
    rng = random.Random(prop_index)
    type_pool = IMAGE_POOL.get(prop_type, IMAGE_POOL["house"])
    # Shuffle and return all 10 images from the type-specific pool
    urls = list(type_pool)
    rng.shuffle(urls)
    return urls


# ═══════════════════════════════════════════════════════════════════════════
# MANAGEMENT COMMAND
# ═══════════════════════════════════════════════════════════════════════════

class Command(BaseCommand):
    help = (
        "Seed the database with demo properties across every district, "
        "municipality, and ward of Nepal (~6,000+ properties with images)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-images", action="store_true",
            help="Skip downloading property images (much faster).",
        )
        parser.add_argument(
            "--province", type=str, default="",
            help="Seed only one province (Koshi, Madhesh, Bagmati, Gandaki, Lumbini, Karnali, Sudurpashchim).",
        )
        parser.add_argument(
            "--district", type=str, default="",
            help="Seed only one district (e.g. Kathmandu, Kaski).",
        )
        parser.add_argument(
            "--clear", action="store_true",
            help="Delete ALL existing properties owned by the seed user first.",
        )
        parser.add_argument(
            "--images-per-property", type=int, default=10,
            help="Number of images per property (default 10, max 10).",
        )

    # -- helpers --

    def _create_user(self):
        user, created = User.objects.get_or_create(
            username="raaz_bhurtel",
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
            self.stdout.write(self.style.SUCCESS("  Created owner: raaz_bhurtel / #Sprs12345"))
        else:
            self.stdout.write("  User 'raaz_bhurtel' exists -- reusing.")
        return user

    def _create_amenities(self):
        amenities = {}
        for item in AMENITIES_DATA:
            obj, _ = Amenity.objects.get_or_create(
                name=item["name"], defaults={"icon": item["icon"]},
            )
            amenities[obj.name] = obj
        self.stdout.write(self.style.SUCCESS(f"  {len(amenities)} amenities ready"))
        return amenities

    def _download_image_pool(self):
        """Download all unique images to a local cache. Returns {url: filepath}."""
        cache_dir = Path(settings.MEDIA_ROOT) / "properties" / "pool"
        cache_dir.mkdir(parents=True, exist_ok=True)

        all_urls = set()
        for urls in IMAGE_POOL.values():
            all_urls.update(urls)

        self.stdout.write(f"  Downloading image pool ({len(all_urls)} unique images)...")
        cache = {}
        ok = 0
        fail = 0

        for url in sorted(all_urls):
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            filepath = cache_dir / f"{url_hash}.jpg"

            if filepath.exists() and filepath.stat().st_size > 1000:
                cache[url] = filepath
                ok += 1
                continue

            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                })
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                with open(filepath, "wb") as f:
                    f.write(data)
                cache[url] = filepath
                ok += 1
                if ok % 10 == 0:
                    self.stdout.write(f"    {ok} images downloaded...")
            except Exception:
                fail += 1

        self.stdout.write(self.style.SUCCESS(f"  Image pool: {ok} downloaded, {fail} failed"))
        return cache

    def _attach_images(self, prop, image_urls, image_cache, max_images):
        """Attach images from the local cache to a property."""
        count = 0
        for img_i, url in enumerate(image_urls[:max_images]):
            filepath = image_cache.get(url)
            if not filepath or not filepath.exists():
                continue
            slug = prop.title[:30].replace(" ", "_").lower()
            slug = "".join(c for c in slug if c.isalnum() or c == "_")
            filename = f"{slug}_w{prop.ward_number}_{img_i}.jpg"
            try:
                with open(filepath, "rb") as f:
                    data = f.read()
                pi = PropertyImage(
                    property=prop,
                    caption=f"{prop.title} - Image {img_i + 1}",
                    is_primary=(img_i == 0),
                )
                pi.image.save(filename, ContentFile(data), save=True)
                count += 1
            except Exception:
                self.stderr.write(self.style.WARNING(
                    f"Skipping image attachment for {prop.title} ({filename}) due to an unexpected error."
                ))
        return count

    # -- main --

    def handle(self, *args, **options):
        skip_images = options.get("no_images", False)
        province_filter = options.get("province", "").strip()
        district_filter = options.get("district", "").strip()
        clear = options.get("clear", False)
        max_images = min(options.get("images_per_property", 10), 10)

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n" + "=" * 60 +
            "\n   SPRS - Seeding All Nepal Properties" +
            "\n   Every District / Municipality / Ward" +
            "\n" + "=" * 60
        ))

        # Filter
        districts = DISTRICTS
        if province_filter:
            districts = [d for d in districts
                         if d["province"].lower() == province_filter.lower()]
            if not districts:
                self.stderr.write(self.style.ERROR(
                    f"No districts for province '{province_filter}'"))
                return
            self.stdout.write(f"  Province filter: {province_filter}")

        if district_filter:
            districts = [d for d in districts
                         if d["name"].lower() == district_filter.lower()]
            if not districts:
                self.stderr.write(self.style.ERROR(
                    f"District '{district_filter}' not found"))
                return
            self.stdout.write(f"  District filter: {district_filter}")

        total_wards = sum(w for d in districts for _, _, w in d["munis"])
        total_munis = sum(len(d["munis"]) for d in districts)
        self.stdout.write(
            f"\n  Scope: {len(districts)} districts, "
            f"{total_munis} municipalities, {total_wards} wards\n"
        )

        # Step 1: User
        self.stdout.write(self.style.MIGRATE_HEADING("Step 1: Owner user"))
        owner = self._create_user()

        if clear:
            count = Property.objects.filter(owner=owner).count()
            if count:
                PropertyImage.objects.filter(property__owner=owner).delete()
                Property.objects.filter(owner=owner).delete()
                self.stdout.write(self.style.WARNING(f"  Cleared {count} existing properties"))

        # Step 2: Amenities
        self.stdout.write(self.style.MIGRATE_HEADING("\nStep 2: Amenities"))
        amenities = self._create_amenities()

        # Step 3: Image pool
        image_cache = {}
        if not skip_images:
            self.stdout.write(self.style.MIGRATE_HEADING("\nStep 3: Image pool"))
            image_cache = self._download_image_pool()

        # Step 4: Properties
        step_num = 3 if skip_images else 4
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nStep {step_num}: Creating properties ({total_wards} wards)"
        ))

        created = 0
        skipped = 0
        errors = 0
        total_imgs = 0
        prop_counter = 0
        start = time.time()

        TYPE_LABELS = {
            "MC": "Metropolitan City", "SMC": "Sub-Metropolitan City",
            "M": "Municipality", "RM": "Rural Municipality",
        }

        for dist_idx, district in enumerate(districts):
            dist_name = district["name"]
            zone = district["zone"]
            munis = district["munis"]
            dist_created = 0

            for muni_idx, (muni_name, muni_type, ward_count) in enumerate(munis):
                muni_full_name = f"{muni_name} {TYPE_LABELS.get(muni_type, 'Municipality')}"

                for ward in range(1, ward_count + 1):
                    prop_counter += 1

                    # Deterministic RNG
                    seed = hashlib.md5(
                        f"{dist_name}-{muni_name}-{ward}".encode()
                    ).hexdigest()
                    rng = random.Random(seed)

                    # Property type (cycle, biased by urban/rural)
                    if muni_type in ("MC", "SMC"):
                        ptype = PROP_TYPES_URBAN[(ward - 1) % len(PROP_TYPES_URBAN)]
                    elif muni_type == "M":
                        ptype = PROP_TYPES_SEMI[(ward - 1) % len(PROP_TYPES_SEMI)]
                    else:
                        ptype = PROP_TYPES_RURAL[(ward - 1) % len(PROP_TYPES_RURAL)]

                    # Rooms
                    r_min, r_max = ROOMS_RANGE[ptype]
                    rooms = rng.randint(r_min, r_max)

                    # Price
                    p_min, p_max = PRICE_RANGES.get((ptype, zone), (5000, 50000))
                    price = rng.randrange(p_min, p_max + 1, 500)

                    # GPS
                    lat, lng = _ward_coords(
                        district["lat"], district["lng"],
                        muni_idx, len(munis), ward, ward_count,
                    )

                    # Title
                    title = _make_title(ptype, muni_name, ward, rooms, dist_name)

                    # Skip duplicates
                    if Property.objects.filter(title=title, owner=owner).exists():
                        skipped += 1
                        continue

                    # Description
                    desc = _make_description(
                        ptype, dist_name, muni_name, muni_type, ward, zone, rooms
                    )

                    # Purpose
                    purpose = rng.choice(RENTAL_PURPOSES.get(ptype, ["any"]))

                    try:
                        prop = Property.objects.create(
                            owner=owner,
                            title=title,
                            property_type=ptype,
                            description=desc,
                            province=district["province"],
                            district=dist_name,
                            municipality=muni_full_name,
                            ward_number=str(ward),
                            address=f"Ward {ward}, {muni_name}, {dist_name}",
                            price=price,
                            num_rooms=rooms,
                            rental_purpose=purpose,
                            latitude=lat,
                            longitude=lng,
                            status="available",
                            contact_phone="9841234567",
                            contact_email="raaz@sprs.com",
                            is_approved=True,
                        )

                        # Amenities
                        chosen = _select_amenities(ptype, amenities, rng)
                        if chosen:
                            prop.amenities.set(chosen)

                        # Images
                        if image_cache:
                            urls = _get_image_urls(ptype, prop_counter)
                            total_imgs += self._attach_images(
                                prop, urls, image_cache, max_images
                            )

                        created += 1
                        dist_created += 1
                    except Exception as exc:
                        errors += 1
                        if errors <= 5:
                            self.stderr.write(self.style.WARNING(
                                f"    Error: {exc}"
                            ))

                    # Progress every 200
                    if created > 0 and created % 200 == 0:
                        elapsed = time.time() - start
                        rate = created / elapsed if elapsed > 0 else 0
                        remaining = total_wards - prop_counter
                        eta = remaining / rate if rate > 0 else 0
                        pct = prop_counter * 100 // total_wards
                        self.stdout.write(
                            f"    [{pct:3d}%] {created}/{total_wards} created "
                            f"| {rate:.1f}/sec | ETA {int(eta)}s"
                        )

            self.stdout.write(
                f"  [{dist_idx+1:>2}/{len(districts)}] {dist_name:<22s} "
                f"({district['province']:<14s}) "
                f"{len(munis):>3d} munis, {dist_created:>3d} properties"
            )

        # Summary
        elapsed = time.time() - start
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n" + "=" * 60 +
            "\n   SEED COMPLETE" +
            "\n" + "=" * 60
        ))
        self.stdout.write(f"  Owner          : raaz_bhurtel (Raaz Bhurtel)")
        self.stdout.write(f"  Amenities      : {len(amenities)}")
        self.stdout.write(f"  Created        : {created}")
        self.stdout.write(f"  Skipped (dups) : {skipped}")
        self.stdout.write(f"  Errors         : {errors}")
        self.stdout.write(f"  Total in DB    : {Property.objects.count()}")
        self.stdout.write(f"  Total Images   : {PropertyImage.objects.filter(property__owner=owner).count()}")
        self.stdout.write(f"  Time           : {elapsed:.1f}s")
        self.stdout.write(self.style.SUCCESS(
            "\n  All Nepal properties seeded successfully!\n"
        ))
