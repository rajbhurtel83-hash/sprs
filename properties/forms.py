from django import forms
from .models import Property, PropertyImage, Amenity, PropertyRequest


class PropertyForm(forms.ModelForm):
    """Form for creating and editing property listings."""

    amenities = forms.ModelMultipleChoiceField(
        queryset=Amenity.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'amenity-checkbox'}),
    )

    class Meta:
        model = Property
        fields = [
            'title', 'property_type', 'description', 'district',
            'municipality', 'ward_number', 'address', 'price',
            'num_rooms', 'rental_purpose', 'amenities',
            'latitude', 'longitude',
            'status', 'contact_phone', 'contact_email',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Property Title'}),
            'property_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe the property...'}),
            'district': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Kathmandu'}),
            'municipality': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Kathmandu Metropolitan City'}),
            'ward_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 10'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full address'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Monthly rent in NPR'}),
            'num_rooms': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'rental_purpose': forms.Select(attrs={'class': 'form-select'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Latitude (click on map)', 'step': '0.0000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Longitude (click on map)', 'step': '0.0000001'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact phone'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Contact email'}),
        }


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
            'placeholder': 'Search by title or description...',
        }),
    )
    property_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + list(Property.PropertyType.choices),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    district = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'District',
        }),
    )
    municipality = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Municipality',
        }),
    )
    ward_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ward No.',
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
        fields = ['request_type', 'move_in_date', 'duration_months', 'message']
        widgets = {
            'request_type': forms.Select(attrs={'class': 'form-select'}),
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
            'move_in_date': 'Preferred Move-in Date',
            'duration_months': 'Rental Duration (months)',
        }

    def clean(self):
        cleaned_data = super().clean()
        request_type = cleaned_data.get('request_type')
        move_in_date = cleaned_data.get('move_in_date')

        if request_type == 'booking' and not move_in_date:
            self.add_error('move_in_date', 'Move-in date is required for a booking request.')

        return cleaned_data
