"""
attach_property_images.py
=========================
Efficiently attach images to all existing properties by referencing
a shared image pool (no file duplication).

Downloads ~65 unique images once, then creates PropertyImage records
that reference these shared pool files. Each property gets 10 images.

Usage:
    python manage.py attach_property_images               # Attach to all
    python manage.py attach_property_images --district Kathmandu
    python manage.py attach_property_images --clear        # Replace existing images
"""

import hashlib
import os
import random
import time
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from properties.models import Property, PropertyImage

# Image pool (same as seed_all_nepal.py)
IMAGE_POOL = {
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
    "room": [
        "https://images.unsplash.com/photo-1540518614846-7eded433c457?w=800&q=80",
        "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=800&q=80",
        "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=800&q=80",
        "https://images.unsplash.com/photo-1616594039964-ae9021a400a0?w=800&q=80",
        "https://images.unsplash.com/photo-1617325247661-675ab4b64ae2?w=800&q=80",
        "https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=800&q=80",
        "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&q=80",
        "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&q=80",
        "https://images.unsplash.com/photo-1560185127-6ed189bf02f4?w=800&q=80",
        "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&q=80",
    ],
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
        "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&q=80",
    ],
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
    "interior": [
        "https://images.unsplash.com/photo-1616137466211-f736a1e16bb4?w=800&q=80",
        "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&q=80",
        "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=800&q=80",
        "https://images.unsplash.com/photo-1556909114-44e3e70034e2?w=800&q=80",
        "https://images.unsplash.com/photo-1600210491369-e753d80a41f3?w=800&q=80",
        "https://images.unsplash.com/photo-1631679706909-1844bbd07221?w=800&q=80",
        "https://images.unsplash.com/photo-1600210491892-03d54c0aaf87?w=800&q=80",
        "https://images.unsplash.com/photo-1600607687644-c7171b42498f?w=800&q=80",
        "https://images.unsplash.com/photo-1560440021-33f9b867899d?w=800&q=80",
        "https://images.unsplash.com/photo-1600566752547-33a26e02886a?w=800&q=80",
    ],
    "nepal_exterior": [
        "https://images.unsplash.com/photo-1544735716-392fe2489ffa?w=800&q=80",
        "https://images.unsplash.com/photo-1605640840605-14ac1855827b?w=800&q=80",
        "https://images.unsplash.com/photo-1526712318848-5f38e2740d44?w=800&q=80",
        "https://images.unsplash.com/photo-1585409677983-0f6c41ca9c3b?w=800&q=80",
        "https://images.unsplash.com/photo-1571401835393-8c5f35328320?w=800&q=80",
        "https://images.unsplash.com/photo-1533130061792-64b345e4a833?w=800&q=80",
        "https://images.unsplash.com/photo-1558799401-1dcba79834c2?w=800&q=80",
        "https://images.unsplash.com/photo-1562462181-bab5b4d3b7c8?w=800&q=80",
        "https://images.unsplash.com/photo-1609766857041-ed402ea8069a?w=800&q=80",
        "https://images.unsplash.com/photo-1602002418816-5c0aeef426aa?w=800&q=80",
    ],
}

CAPTIONS = {
    "house": ["Front exterior view", "Living room", "Bedroom", "Kitchen area",
              "Bathroom", "Backyard/garden", "Interior hallway", "Neighborhood view",
              "Local surroundings", "Street view"],
    "apartment": ["Building exterior", "Living space", "Master bedroom", "Kitchen",
                   "Bathroom", "Balcony view", "Lobby/entrance", "Neighborhood",
                   "Local area", "Nearby facilities"],
    "room": ["Room interior", "Window view", "Storage area", "Attached bathroom",
             "Room entrance", "Balcony", "Building exterior", "Neighborhood",
             "Local surroundings", "Street view"],
    "flat": ["Living room", "Master bedroom", "Kitchen", "Bathroom",
             "Balcony view", "Dining area", "Building exterior", "Neighborhood",
             "Local area", "Street view"],
    "land": ["Plot front view", "Plot overview", "Road access", "Surrounding area",
             "Boundary markers", "Nearby development", "Landscape view",
             "Neighborhood", "Local infrastructure", "Aerial perspective"],
    "commercial": ["Storefront/entrance", "Interior space", "Counter area",
                    "Back office", "Parking area", "Street visibility",
                    "Building exterior", "Neighborhood", "Local market",
                    "Nearby facilities"],
}


def _url_to_pool_path(url):
    """Convert a URL to a pool file relative path (relative to MEDIA_ROOT)."""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return f"properties/pool/{url_hash}.jpg"


def _get_image_paths(prop_type, prop_id):
    """Return 10 pool image paths for a property (relative to MEDIA_ROOT)."""
    rng = random.Random(prop_id)
    urls = []
    type_pool = IMAGE_POOL.get(prop_type, IMAGE_POOL["house"])
    urls.extend(rng.sample(type_pool, min(4, len(type_pool))))
    urls.extend(rng.sample(IMAGE_POOL["interior"], min(3, len(IMAGE_POOL["interior"]))))
    urls.extend(rng.sample(IMAGE_POOL["nepal_exterior"], min(3, len(IMAGE_POOL["nepal_exterior"]))))
    return [_url_to_pool_path(u) for u in urls[:10]]


class Command(BaseCommand):
    help = "Efficiently attach 10 images to every property using a shared image pool."

    def add_arguments(self, parser):
        parser.add_argument(
            "--district", type=str, default="",
            help="Only attach images for a specific district.",
        )
        parser.add_argument(
            "--clear", action="store_true",
            help="Remove existing images before attaching new ones.",
        )
        parser.add_argument(
            "--images-per-property", type=int, default=10,
            help="Number of images per property (default 10).",
        )

    def _download_pool(self):
        """Download all unique pool images to MEDIA_ROOT/properties/pool/."""
        pool_dir = Path(settings.MEDIA_ROOT) / "properties" / "pool"
        pool_dir.mkdir(parents=True, exist_ok=True)

        all_urls = set()
        for urls in IMAGE_POOL.values():
            all_urls.update(urls)

        self.stdout.write(f"  Checking image pool ({len(all_urls)} unique images)...")
        downloaded = 0
        already = 0
        failed = 0

        for url in sorted(all_urls):
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            filepath = pool_dir / f"{url_hash}.jpg"

            if filepath.exists() and filepath.stat().st_size > 1000:
                already += 1
                continue

            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                })
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                with open(filepath, "wb") as f:
                    f.write(data)
                downloaded += 1
                if (downloaded + already) % 10 == 0:
                    self.stdout.write(f"    {downloaded + already} processed...")
            except Exception as exc:
                failed += 1
                self.stderr.write(f"    Failed: {url[:60]}... ({exc})")

        self.stdout.write(self.style.SUCCESS(
            f"  Pool: {already} cached, {downloaded} downloaded, {failed} failed"
        ))
        return already + downloaded

    def handle(self, *args, **options):
        district_filter = options.get("district", "").strip()
        clear = options.get("clear", False)
        max_images = min(options.get("images_per_property", 10), 10)

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n" + "=" * 60 +
            "\n   Attaching Images to Properties" +
            "\n" + "=" * 60
        ))

        # Step 1: Download pool
        self.stdout.write(self.style.MIGRATE_HEADING("\nStep 1: Image pool"))
        pool_count = self._download_pool()

        if pool_count == 0:
            self.stderr.write(self.style.ERROR("  No images available. Aborting."))
            return

        # Step 2: Get properties
        properties = Property.objects.all().order_by("id")
        if district_filter:
            properties = properties.filter(district__iexact=district_filter)
            self.stdout.write(f"  District filter: {district_filter}")

        total = properties.count()
        self.stdout.write(f"  Properties to process: {total}")

        # Filter to properties without images (unless --clear)
        if clear:
            PropertyImage.objects.filter(property__in=properties).delete()
            self.stdout.write(self.style.WARNING("  Cleared existing images"))
            props_needing_images = properties
        else:
            # Only attach to properties that don't have images yet
            props_with_images = PropertyImage.objects.values_list(
                "property_id", flat=True
            ).distinct()
            props_needing_images = properties.exclude(id__in=props_with_images)

        to_process = props_needing_images.count()
        self.stdout.write(f"  Properties needing images: {to_process}")

        if to_process == 0:
            self.stdout.write(self.style.SUCCESS("  All properties already have images!"))
            return

        # Step 3: Bulk create PropertyImage records
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nStep 2: Creating image records ({to_process} × {max_images} = {to_process * max_images})"
        ))

        media_root = Path(settings.MEDIA_ROOT)
        created = 0
        batch = []
        batch_size = 500
        start = time.time()

        for prop_idx, prop in enumerate(props_needing_images.iterator()):
            paths = _get_image_paths(prop.property_type, prop.id)
            captions = CAPTIONS.get(prop.property_type, CAPTIONS["house"])

            for img_i, path in enumerate(paths[:max_images]):
                # Verify the pool file exists
                full_path = media_root / path
                if not full_path.exists():
                    continue

                batch.append(PropertyImage(
                    property=prop,
                    image=path,
                    caption=f"{prop.title} - {captions[img_i % len(captions)]}",
                    is_primary=(img_i == 0),
                ))

            # Bulk create when batch is full
            if len(batch) >= batch_size:
                PropertyImage.objects.bulk_create(batch, batch_size=batch_size)
                created += len(batch)
                batch = []

                elapsed = time.time() - start
                rate = created / elapsed if elapsed > 0 else 0
                remaining = (to_process * max_images) - created
                eta = remaining / rate if rate > 0 else 0
                pct = created * 100 // (to_process * max_images)
                self.stdout.write(
                    f"    [{pct:3d}%] {created} images created "
                    f"| {rate:.0f}/sec | ETA {int(eta)}s"
                )

        # Final batch
        if batch:
            PropertyImage.objects.bulk_create(batch, batch_size=batch_size)
            created += len(batch)

        elapsed = time.time() - start
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n" + "=" * 60 +
            "\n   IMAGE ATTACHMENT COMPLETE" +
            "\n" + "=" * 60
        ))
        self.stdout.write(f"  Images created : {created}")
        self.stdout.write(f"  Total in DB    : {PropertyImage.objects.count()}")
        self.stdout.write(f"  Time           : {elapsed:.1f}s")
        self.stdout.write(self.style.SUCCESS("\n  All property images attached successfully!\n"))
