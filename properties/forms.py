from django import forms
from .models import (
    Property,
    PropertyImage,
    Amenity,
    PropertyRequest,
    get_canonical_district_choices,
    normalize_nepal_district,
)


class PropertyForm(forms.ModelForm):
    """Form for creating and editing property listings."""

    price = forms.DecimalField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Monthly rent in NPR'}),
    )

    district = forms.ChoiceField(
        choices=[('', 'Select District')] + list(get_canonical_district_choices()),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    amenities = forms.ModelMultipleChoiceField(
        queryset=Amenity.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'amenity-checkbox'}),
    )

    class Meta:
        model = Property
        fields = [
            'title', 'property_type', 'description', 'province', 'district',
            'municipality', 'ward_number', 'address', 'price',
            'num_rooms', 'rental_purpose', 'amenities',
            'total_area', 'floor_number', 'facing_direction', 'road_access_width',
            'furnishing_status', 'available_from', 'minimum_rental_duration', 'maximum_occupants',
            'property_overview', 'amenity_settings', 'nearby_places', 'house_rules',
            'owner_citizenship', 'ownership_certificate', 'land_tax_receipt', 'utility_bill', 'live_selfie',
            'owner_verified', 'government_id_verified', 'ownership_document_verified', 'utility_bill_verified',
            'phone_verified', 'email_verified', 'location_verified', 'recently_inspected', 'verification_date',
            'is_verified',
            'latitude', 'longitude',
            'status', 'contact_phone', 'contact_email',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Property Title'}),
            'property_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe the property...'}),
            'province': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Bagmati'}),
            'district': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Kathmandu'}),
            'municipality': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Kathmandu Metropolitan City'}),
            'ward_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 10'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full address'}),
            'num_rooms': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'rental_purpose': forms.Select(attrs={'class': 'form-select'}),
            'total_area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1200 sq ft'}),
            'floor_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 3rd Floor'}),
            'facing_direction': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., East-facing'}),
            'road_access_width': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 20 ft road access'}),
            'furnishing_status': forms.Select(attrs={'class': 'form-select'}),
            'available_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'minimum_rental_duration': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Months'}),
            'maximum_occupants': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'People'}),
            'property_overview': forms.Textarea(attrs={'class': 'form-control', 'rows': 7, 'placeholder': '{"balcony": true, "natural_lighting": "Excellent", "nearby_landmarks": "..."}'}),
            'amenity_settings': forms.Textarea(attrs={'class': 'form-control', 'rows': 7, 'placeholder': '{"1": {"status": "included"}, "2": {"status": "extra", "monthly_charge": 800}}'}),
            'nearby_places': forms.Textarea(attrs={'class': 'form-control', 'rows': 7, 'placeholder': '[{"type": "Hospital", "name": "KMC Hospital", "distance": "350 meters"}]'}),
            'house_rules': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Quiet hours, pet policy, smoking rules, etc.'}),
            'owner_citizenship': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'ownership_certificate': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'land_tax_receipt': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'utility_bill': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'live_selfie': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'owner_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'government_id_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ownership_document_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'utility_bill_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'phone_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'location_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'recently_inspected': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'verification_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Latitude (click on map)', 'step': '0.0000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Longitude (click on map)', 'step': '0.0000001'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit contact phone', 'maxlength': '10'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Contact email'}),
        }

    def clean_property_overview(self):
        value = self.cleaned_data.get('property_overview') or {}
        return value

    def clean_district(self):
        district = self.cleaned_data.get('district')
        return normalize_nepal_district(district)

    def clean_amenity_settings(self):
        value = self.cleaned_data.get('amenity_settings') or {}
        return value

    def clean_nearby_places(self):
        value = self.cleaned_data.get('nearby_places') or []
        return value

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError('Price cannot be negative.')
        return price

    def clean_contact_phone(self):
        contact_phone = (self.cleaned_data.get('contact_phone') or '').strip()
        if not contact_phone:
            return contact_phone
        if not contact_phone.isdigit() or len(contact_phone) != 10:
            raise forms.ValidationError('Contact phone must be exactly 10 digits.')
        return contact_phone

    def clean_contact_email(self):
        contact_email = (self.cleaned_data.get('contact_email') or '').strip()
        return contact_email.lower() if contact_email else contact_email


class PropertyImageForm(forms.ModelForm):
    """Form for uploading property images."""

    class Meta:
        model = PropertyImage
        fields = ['image', 'caption']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Image caption (optional)'}),
        }


class PropertySearchForm(forms.Form):
    """Form for searching/filtering properties."""

    keyword = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by title, district, landmark, or road...',
        }),
    )
    property_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + list(Property.PropertyType.choices),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    province = forms.CharField(
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_province',
        }),
    )
    district = forms.CharField(
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_district',
        }),
    )
    municipality = forms.CharField(
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_municipality',
        }),
    )
    ward_number = forms.CharField(
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_ward_number',
        }),
    )
    min_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min Price',
        }),
    )
    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max Price',
        }),
    )
    num_rooms = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min Rooms',
        }),
    )
    rental_purpose = forms.ChoiceField(
        required=False,
        choices=[('', 'Any Purpose')] + list(Property.RentalPurpose.choices),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    sort = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Newest First'),
            ('price_asc', 'Price: Low to High'),
            ('price_desc', 'Price: High to Low'),
            ('newest', 'Newest First'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )


class PropertyRequestForm(forms.ModelForm):
    """Form for requesting a property visit, inquiry, or booking."""

    class Meta:
        model = PropertyRequest
        fields = ['request_type', 'visit_date', 'visit_time', 'move_in_date', 'duration_months', 'message']
        widgets = {
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'visit_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'visit_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
            }),
            'move_in_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'duration_months': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 60,
                'placeholder': 'e.g. 6',
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add any additional details or questions...',
            }),
        }
        labels = {
            'visit_date': 'Preferred Visit Date',
            'visit_time': 'Preferred Visit Time',
            'move_in_date': 'Preferred Move-in Date',
            'duration_months': 'Rental Duration (months)',
        }

    def clean(self):
        cleaned_data = super().clean()
        request_type = cleaned_data.get('request_type')
        move_in_date = cleaned_data.get('move_in_date')
        visit_date = cleaned_data.get('visit_date')
        visit_time = cleaned_data.get('visit_time')

        if request_type == 'booking' and not move_in_date:
            self.add_error('move_in_date', 'Move-in date is required for a booking request.')

        if request_type == 'visit':
            if not visit_date:
                self.add_error('visit_date', 'Visit date is required for a visit request.')
            if not visit_time:
                self.add_error('visit_time', 'Visit time is required for a visit request.')

        return cleaned_data
