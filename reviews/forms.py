from django import forms

from reviews.models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = [
            'rating', 'cleanliness', 'location', 'owner_behavior', 'value_for_money',
            'security', 'water_supply', 'internet_quality', 'parking', 'comment',
        ]
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 5,
            }),
            'cleanliness': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5, 'placeholder': 'Optional 1-5'}),
            'location': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5, 'placeholder': 'Optional 1-5'}),
            'owner_behavior': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5, 'placeholder': 'Optional 1-5'}),
            'value_for_money': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5, 'placeholder': 'Optional 1-5'}),
            'security': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5, 'placeholder': 'Optional 1-5'}),
            'water_supply': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5, 'placeholder': 'Optional 1-5'}),
            'internet_quality': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5, 'placeholder': 'Optional 1-5'}),
            'parking': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5, 'placeholder': 'Optional 1-5'}),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your experience...',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        for field in ['cleanliness', 'location', 'owner_behavior', 'value_for_money', 'security', 'water_supply', 'internet_quality', 'parking']:
            value = cleaned_data.get(field)
            if value in ('', None):
                cleaned_data[field] = None
        return cleaned_data
