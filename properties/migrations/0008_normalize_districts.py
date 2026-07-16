from django.db import migrations


def normalize_districts(apps, schema_editor):
    Property = apps.get_model('properties', 'Property')

    canonical = {}
    for entry in [
        ('Achham', 'Achham'), ('Arghakhanchi', 'Arghakhanchi'), ('Baglung', 'Baglung'),
        ('Baitadi', 'Baitadi'), ('Bajhang', 'Bajhang'), ('Bajura', 'Bajura'),
        ('Banke', 'Banke'), ('Bara', 'Bara'), ('Bardiya', 'Bardiya'),
        ('Bhaktapur', 'Bhaktapur'), ('Bhojpur', 'Bhojpur'), ('Chitwan', 'Chitwan'),
        ('Dadeldhura', 'Dadeldhura'), ('Dailekh', 'Dailekh'), ('Dang', 'Dang'),
        ('Darchula', 'Darchula'), ('Dhading', 'Dhading'), ('Dhankuta', 'Dhankuta'),
        ('Dhanusha', 'Dhanusha'), ('Dolakha', 'Dolakha'), ('Dolpa', 'Dolpa'), ('Doti', 'Doti'),
        ('Eastern Rukum', 'Eastern Rukum'), ('Gorkha', 'Gorkha'), ('Gulmi', 'Gulmi'),
        ('Humla', 'Humla'), ('Ilam', 'Ilam'), ('Jajarkot', 'Jajarkot'), ('Jhapa', 'Jhapa'),
        ('Jumla', 'Jumla'), ('Kailali', 'Kailali'), ('Kalikot', 'Kalikot'),
        ('Kanchanpur', 'Kanchanpur'), ('Kapilvastu', 'Kapilvastu'), ('Kaski', 'Kaski'),
        ('Kathmandu', 'Kathmandu'), ('Kavrepalanchok', 'Kavrepalanchok'), ('Khotang', 'Khotang'),
        ('Lalitpur', 'Lalitpur'), ('Lamjung', 'Lamjung'), ('Mahottari', 'Mahottari'),
        ('Makwanpur', 'Makwanpur'), ('Manang', 'Manang'), ('Morang', 'Morang'), ('Mugu', 'Mugu'),
        ('Mustang', 'Mustang'), ('Myagdi', 'Myagdi'), ('Nawalpur', 'Nawalpur'), ('Nuwakot', 'Nuwakot'),
        ('Okhaldhunga', 'Okhaldhunga'), ('Palpa', 'Palpa'), ('Panchthar', 'Panchthar'),
        ('Parasi', 'Parasi'), ('Parbat', 'Parbat'), ('Parsa', 'Parsa'), ('Pyuthan', 'Pyuthan'),
        ('Ramechhap', 'Ramechhap'), ('Rasuwa', 'Rasuwa'), ('Rautahat', 'Rautahat'), ('Rolpa', 'Rolpa'),
        ('Rupandehi', 'Rupandehi'), ('Salyan', 'Salyan'), ('Sankhuwasabha', 'Sankhuwasabha'),
        ('Saptari', 'Saptari'), ('Sarlahi', 'Sarlahi'), ('Sindhuli', 'Sindhuli'),
        ('Sindhupalchok', 'Sindhupalchok'), ('Siraha', 'Siraha'), ('Solukhumbu', 'Solukhumbu'),
        ('Sunsari', 'Sunsari'), ('Surkhet', 'Surkhet'), ('Syangja', 'Syangja'), ('Tanahun', 'Tanahun'),
        ('Taplejung', 'Taplejung'), ('Terhathum', 'Terhathum'), ('Udayapur', 'Udayapur'),
        ('Western Rukum', 'Western Rukum'),
    ]:
        canonical[entry[0].lower()] = entry[1]

    updates = []
    for prop in Property.objects.exclude(district='').only('id', 'district'):
        normalized = canonical.get((prop.district or '').strip().lower())
        if normalized and prop.district != normalized:
            prop.district = normalized
            updates.append(prop)

    if updates:
        Property.objects.bulk_update(updates, ['district'])


def noop_reverse(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0007_propertyrequest_visit_date_and_more'),
    ]

    operations = [
        migrations.RunPython(normalize_districts, noop_reverse),
    ]