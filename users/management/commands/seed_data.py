from django.core.management.base import BaseCommand
from users.models import User
from properties.models import Property


class Command(BaseCommand):
    help = 'Seed the database with sample data for development.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # Create admin user
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@sprs.com',
                password='admin123',
                first_name='System',
                last_name='Admin',
                role='admin',
            )
            self.stdout.write(self.style.SUCCESS('Created admin user (admin/admin123)'))

        # Create sample owner
        owner, created = User.objects.get_or_create(
            username='owner1',
            defaults={
                'email': 'owner1@sprs.com',
                'first_name': 'Ram',
                'last_name': 'Sharma',
                'role': 'owner',
                'phone': '9841000001',
                'address': 'Kathmandu, Nepal',
            }
        )
        if created:
            owner.set_password('owner123')
            owner.save()
            self.stdout.write(self.style.SUCCESS('Created owner user (owner1/owner123)'))

        # Create sample tenant
        tenant, created = User.objects.get_or_create(
            username='tenant1',
            defaults={
                'email': 'tenant1@sprs.com',
                'first_name': 'Sita',
                'last_name': 'Thapa',
                'role': 'tenant',
                'phone': '9841000002',
                'address': 'Lalitpur, Nepal',
            }
        )
        if created:
            tenant.set_password('tenant123')
            tenant.save()
            self.stdout.write(self.style.SUCCESS('Created tenant user (tenant1/tenant123)'))

        # Create sample properties
        sample_properties = [
            {
                'title': '2BHK Flat in Baneshwor',
                'property_type': 'flat',
                'description': 'A spacious 2 bedroom flat with attached bathroom, kitchen, and living room. Well ventilated with natural sunlight. Close to main road and market area.',
                'district': 'Kathmandu',
                'ward_number': '10',
                'address': 'New Baneshwor, Kathmandu',
                'price': 15000,
                'num_rooms': 2,
                'contact_phone': '9841000001',
                'contact_email': 'owner1@sprs.com',
            },
            {
                'title': 'Single Room in Kupondole',
                'property_type': 'room',
                'description': 'A well-furnished single room suitable for a student or working professional. Common kitchen and bathroom available. Safe and quiet neighborhood.',
                'district': 'Lalitpur',
                'ward_number': '5',
                'address': 'Kupondole, Lalitpur',
                'price': 5000,
                'num_rooms': 1,
                'contact_phone': '9841000001',
                'contact_email': 'owner1@sprs.com',
            },
            {
                'title': 'House for Rent in Bhaktapur',
                'property_type': 'house',
                'description': 'A complete 2-storey house with 4 bedrooms, 2 bathrooms, spacious kitchen and a garden area. Ideal for family living. Parking space available.',
                'district': 'Bhaktapur',
                'ward_number': '8',
                'address': 'Kamalbinayak, Bhaktapur',
                'price': 35000,
                'num_rooms': 4,
                'contact_phone': '9841000001',
                'contact_email': 'owner1@sprs.com',
            },
            {
                'title': 'Commercial Space in Thamel',
                'property_type': 'commercial',
                'description': 'Prime commercial space on the ground floor suitable for a shop or office. High foot traffic area in the heart of Thamel tourist district.',
                'district': 'Kathmandu',
                'ward_number': '26',
                'address': 'Thamel, Kathmandu',
                'price': 50000,
                'num_rooms': 1,
                'contact_phone': '9841000001',
                'contact_email': 'owner1@sprs.com',
            },
            {
                'title': '3BHK Flat in Jhamsikhel',
                'property_type': 'flat',
                'description': 'Modern 3 bedroom flat with modular kitchen, attached bathrooms, and a balcony with mountain view. Located in a peaceful residential area.',
                'district': 'Lalitpur',
                'ward_number': '3',
                'address': 'Jhamsikhel, Lalitpur',
                'price': 25000,
                'num_rooms': 3,
                'contact_phone': '9841000001',
                'contact_email': 'owner1@sprs.com',
            },
        ]

        for prop_data in sample_properties:
            prop, created = Property.objects.get_or_create(
                title=prop_data['title'],
                owner=owner,
                defaults=prop_data,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created property: {prop.title}'))

        self.stdout.write(self.style.SUCCESS('\nDatabase seeding completed!'))
        self.stdout.write('\nSample Accounts:')
        self.stdout.write('  Admin:  admin / admin123')
        self.stdout.write('  Owner:  owner1 / owner123')
        self.stdout.write('  Tenant: tenant1 / tenant123')
