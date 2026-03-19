import json
from django import forms
from .models import AIResponse

class AIResponseAdminForm(forms.ModelForm):
    class Meta:
        model = AIResponse
        fields = '__all__'
        widgets = {
            'complex_forecast': forms.Textarea(attrs={
                'rows': 4, 
                'placeholder': '[{"choice": "Option A", "confidence": 50.0}, ...]'
            }),
        }

    def clean_complex_forecast(self):
        data = self.cleaned_data.get('complex_forecast')
        if not data:
            return data
            
        # If it's a string (from manual input), validate it's proper JSON
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format. Please use double quotes and standard JSON syntax.")
        
        return data

    def clean(self):
        cleaned_data = super().clean()
        run = cleaned_data.get('run')
        if not run:
            return cleaned_data
            
        q_type = run.question.question_type
        score = cleaned_data.get('normalized_score')
        complex_forecast = cleaned_data.get('complex_forecast')
        is_refusal = cleaned_data.get('is_refusal')

        if is_refusal:
            return cleaned_data

        if q_type in ['SUBJECTIVE_SLIDER', 'PREDICTIVE_BINARY']:
            if score is None:
                raise forms.ValidationError(f"Question type {q_type} requires a Normalized Score (0-100).")
        
        elif q_type == 'PREDICTIVE_CHOICE':
            if not complex_forecast or not isinstance(complex_forecast, list):
                raise forms.ValidationError("Predictive Choice requires a JSON list of objects in complex_forecast, where complex_forecast keys are choice and confidence.")
            
            try:
                total = sum(float(item.get('confidence', 0)) for item in complex_forecast)
                if not (99.8 <= total <= 100.2): # Allow for slight float rounding
                    raise forms.ValidationError(f"Total confidence must sum to 100%. Current: {total}%")
            except (TypeError, ValueError):
                raise forms.ValidationError("Each item in the list must have a numerical 'confidence' key.")

        return cleaned_data