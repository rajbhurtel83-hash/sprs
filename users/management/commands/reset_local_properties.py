import random
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from properties.models import Amenity, Property, PropertyImage
from users.management.commands.nepal_data import DISTRICTS
from users.models import User


TARGET_DISTRICTS = [
    'Kathmandu',
    'Bhaktapur',
    'Lalitpur',
    'Kavrepalanchok',
]

DISTRICT_ALIASES = {
    'Kathmandu': ['kathmandu'],
    'Bhaktapur': ['bhaktapur'],
    'Lalitpur': ['lalitpur'],
    'Kavrepalanchok': ['kavre', 'kavrepalanchok', 'kavrepala'],
}

DISTRICT_CENTERS = {
    'Kathmandu': (27.7172, 85.3240),
    'Bhaktapur': (27.6710, 85.4298),
    'Lalitpur': (27.6644, 85.3188),
    'Kavrepalanchok': (27.6200, 85.5250),
}

PROPERTY_PROFILES = {
    'room': {
        'title': 'Room',
        'price': (3500, 12000),
        'rooms': (1, 1),
        'purpose': 'student',
        'furnishing': Property.FurnishingStatus.UNFURNISHED,
        'amenities': ['Electricity', 'Water Supply', 'Attached Bathroom', 'Road Access'],
        'landmarks': ['local market', 'bus stop', 'community school'],
    },
    'flat': {
        'title': 'Flat',
        'price': (12000, 35000),
        'rooms': (1, 3),
        'purpose': 'family',
        'furnishing': Property.FurnishingStatus.SEMI_FURNISHED,
        'amenities': ['Electricity', 'Water Supply', 'Kitchen', 'Attached Bathroom', 'Balcony'],
        'landmarks': ['ring road access', 'nearby pharmacy', 'local school'],
    },
    'apartment': {
        'title': 'Apartment',
        'price': (18000, 55000),
        'rooms': (2, 4),
        'purpose': 'family',
        'furnishing': Property.FurnishingStatus.FURNISHED,
        'amenities': ['Electricity', 'Water Supply', 'Kitchen', 'Attached Bathroom', 'Parking', 'Security'],
        'landmarks': ['shopping area', 'hospital', 'public transport'],
    },
    'house': {
        'title': 'House',
        'price': (18000, 80000),
        'rooms': (2, 6),
        'purpose': 'family',
        'furnishing': Property.FurnishingStatus.SEMI_FURNISHED,
        'amenities': ['Electricity', 'Water Supply', 'Kitchen', 'Attached Bathroom', 'Parking', 'Garden'],
        'landmarks': ['main road', 'school', 'market'],
    },
    'commercial': {
        'title': 'Commercial Space',
        'price': (25000, 90000),
        'rooms': (1, 4),
        'purpose': 'office',
        'furnishing': Property.FurnishingStatus.UNFURNISHED,
        'amenities': ['Electricity', 'Water Supply', 'Road Access', 'Parking', 'CCTV'],
        'landmarks': ['busy street', 'bank', 'commercial hub'],
    },
    'land': {
        'title': 'Land Plot',
        'price': (50000, 450000),
        'rooms': (0, 0),
        'purpose': 'any',
        'furnishing': Property.FurnishingStatus.UNFURNISHED,
        'amenities': ['Road Access', 'Electricity'],
        'landmarks': ['road frontage', 'development area', 'utility access'],
    },
}

PROPERTY_SEQUENCE = ['room', 'flat', 'apartment', 'house', 'commercial', 'land']

HOUSE_RULES = 'No smoking indoors. No loud music after 9 PM. Keep the property clean and respect neighbors.'

AMENITY_ICON_MAP = {
    'WiFi': 'bi-wifi',
    'Parking': 'bi-car-front',
    'Water Supply': 'bi-droplet',
    'Electricity': 'bi-lightning',
    'Balcony': 'bi-building',
    'Garden': 'bi-tree',
    'Security': 'bi-shield-check',
    'Nearby School': 'bi-mortarboard',
    'Nearby Hospital': 'bi-hospital',
    'Road Access': 'bi-signpost',
    'Kitchen': 'bi-cup-hot',
    'Attached Bathroom': 'bi-droplet-half',
    'Furnished': 'bi-lamp',
    'CCTV': 'bi-camera-video',
    'Earthquake Resistant': 'bi-house-check',
}


class Command(BaseCommand):
    help = 'Delete all properties and seed 300 local properties for Kathmandu valley and Kavrepalanchok.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=300, help='Number of properties to keep after reseeding.')

    def _district_lookup(self):
        lookup = {district['name']: district for district in DISTRICTS}
        selected = []
        for district_name in TARGET_DISTRICTS:
            district = lookup.get(district_name)
            if district:
                selected.append(district)
        return selected

    def _collect_images(self):
        media_root = Path(settings.MEDIA_ROOT)
        property_root = media_root / 'properties'
        candidates = []

        if property_root.exists():
            for path in property_root.rglob('*'):
                if not path.is_file() or path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
                    continue
                lower_name = path.name.lower()
                for district_name, aliases in DISTRICT_ALIASES.items():
                    if any(alias in lower_name for alias in aliases):
                        candidates.append((district_name, path))
                        break

        grouped = {district_name: [] for district_name in TARGET_DISTRICTS}
        for district_name, path in candidates:
            grouped.setdefault(district_name, []).append(path)

        for district_name in grouped:
            grouped[district_name] = sorted({str(path) for path in grouped[district_name]})

        return grouped

    def _seed_amenities(self):
        for amenity_name, icon in AMENITY_ICON_MAP.items():
            Amenity.objects.get_or_create(name=amenity_name, defaults={'icon': icon})

    def _ensure_owner(self):
        owner, created = User.objects.get_or_create(
            username='sprs_demo_owner',
            defaults={
                'email': 'sprs.demo.owner@gmail.com',
                'first_name': 'SPRS',
                'last_name': 'Owner',
                'role': User.Role.OWNER,
                'is_active': True,
            },
        )
        if created:
            owner.set_password('demo-owner-12345')
            owner.save()
        return owner

    def _build_property_payload(self, rng, district, municipality_name, ward_number, property_type, index):
        profile = PROPERTY_PROFILES[property_type]
        title = f"{profile['title']} in {municipality_name}, Ward {ward_number}, {district['name']}"
        landmark = rng.choice(profile['landmarks'])
        bed_min, bed_max = profile['rooms']
        rooms = rng.randint(bed_min, bed_max) if bed_max > 0 else 0
        price_low, price_high = profile['price']
        price = Decimal(rng.randint(price_low, price_high))
        phone = f"98{rng.randint(1000000, 9999999):07d}"
        email_slug = f"property{index + 1}.{district['name'].lower()}.{municipality_name.lower().replace(' ', '')}"

        center_lat, center_lng = DISTRICT_CENTERS[district['name']]
        offset = (index % 11) * 0.0025
        latitude = Decimal(str(round(center_lat + offset, 7)))
        longitude = Decimal(str(round(center_lng + offset, 7)))

        overview = {
            'bedrooms': rooms,
            'bathrooms': max(1, rooms or 1),
            'parking': property_type in {'house', 'apartment', 'commercial'},
            'furnished': profile['furnishing'] == Property.FurnishingStatus.FURNISHED,
            'district': district['name'],
            'municipality': municipality_name,
            'ward': ward_number,
        }

        nearby_places = [
            {'name': landmark, 'type': 'Landmark', 'distance': f"{rng.randint(100, 900)} m"},
            {'name': 'Local market', 'type': 'Market', 'distance': f"{rng.randint(150, 1200)} m"},
            {'name': 'Public transport stop', 'type': 'Transport', 'distance': f"{rng.randint(80, 800)} m"},
        ]

        return {
            'title': title,
            'property_type': property_type,
            'description': (
                f"A {property_type} located in Ward {ward_number}, {municipality_name}, {district['name']}. "
                f"It offers reliable water, electricity, and easy access to {landmark}. "
                f"This listing is part of the local 300-property reset and uses real district-tagged photos."
            ),
            'province': district['province'],
            'district': district['name'],
            'municipality': municipality_name,
            'ward_number': str(ward_number),
            'address': f"Ward {ward_number}, {municipality_name}, {district['name']}",
            'price': price,
            'num_rooms': rooms or 1,
            'rental_purpose': profile['purpose'],
            'total_area': f"{rng.randint(500, 2400)} sq ft",
            'floor_number': 'Ground Floor' if property_type in {'land', 'commercial'} else f"{rng.randint(1, 5)}th Floor",
            'facing_direction': rng.choice(['East', 'West', 'North', 'South']) + '-facing',
            'road_access_width': f"{rng.randint(8, 30)} ft road access",
            'furnishing_status': profile['furnishing'],
            'available_from': timezone.now().date(),
            'minimum_rental_duration': rng.randint(6, 24),
            'maximum_occupants': max(1, rooms + rng.randint(0, 3)),
            'property_overview': overview,
            'amenity_settings': {},
            'nearby_places': nearby_places,
            'house_rules': HOUSE_RULES,
            'latitude': latitude,
            'longitude': longitude,
            'status': Property.Status.AVAILABLE,
            'contact_phone': phone,
            'contact_email': f"{email_slug}@gmail.com",
            'is_approved': True,
            'owner_verified': True,
            'government_id_verified': True,
            'ownership_document_verified': True,
            'utility_bill_verified': True,
            'phone_verified': True,
            'email_verified': True,
            'location_verified': True,
            'recently_inspected': True,
            'verification_date': timezone.now(),
            'is_verified': True,
        }

    def _attach_images(self, property_obj, image_paths, index):
        selected_paths = image_paths[:3]
        if not selected_paths:
            return

        for image_index, image_path in enumerate(selected_paths):
            source_path = Path(image_path)
            with open(source_path, 'rb') as source_file:
                content = ContentFile(source_file.read())
            caption = f"{property_obj.title} image {image_index + 1}"
            property_image = PropertyImage(property=property_obj, caption=caption, is_primary=(image_index == 0))
            property_image.image.save(
                f'reset_{index + 1:03d}_{image_index + 1}{source_path.suffix.lower()}',
                content,
                save=True,
            )

    def handle(self, *args, **options):
        limit = max(1, options['limit'])
        rng = random.Random(20260714)

        districts = self._district_lookup()
        if not districts:
            self.stderr.write(self.style.ERROR('No target districts found in Nepal data.'))
            return

        image_groups = self._collect_images()
        owner = self._ensure_owner()
        self._seed_amenities()

        amenities_by_name = {amenity.name: amenity for amenity in Amenity.objects.all()}

        self.stdout.write(self.style.MIGRATE_HEADING('\n' + '=' * 60))
        self.stdout.write(self.style.MIGRATE_HEADING('  Resetting properties to 300 local listings'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60))

        with transaction.atomic():
            PropertyImage.objects.all().delete()
            deleted_count, _ = Property.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'  Removed {deleted_count} existing property records.'))

            created_properties = []
            for index in range(limit):
                district = districts[index % len(districts)]
                municipality_name, _, ward_count = rng.choice(district['munis'])
                ward_number = rng.randint(1, ward_count)
                property_type = PROPERTY_SEQUENCE[index % len(PROPERTY_SEQUENCE)]
                payload = self._build_property_payload(rng, district, municipality_name, ward_number, property_type, index)
                property_obj = Property.objects.create(owner=owner, **payload)

                amenity_names = PROPERTY_PROFILES[property_type]['amenities']
                property_obj.amenities.set([amenities_by_name[name] for name in amenity_names if name in amenities_by_name])

                district_images = image_groups.get(district['name']) or []
                if not district_images:
                    district_images = [path for paths in image_groups.values() for path in paths]
                if district_images:
                    image_start = (index * 3) % len(district_images)
                    selected_images = [district_images[(image_start + offset) % len(district_images)] for offset in range(min(3, len(district_images)))]
                    self._attach_images(property_obj, selected_images, index)

                created_properties.append(property_obj)

        self.stdout.write(self.style.SUCCESS(f'  Seeded {len(created_properties)} properties across Kathmandu, Bhaktapur, Lalitpur, and Kavrepalanchok.'))