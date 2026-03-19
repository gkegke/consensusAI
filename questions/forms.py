from django import forms
from .models import Question

class QuestionSubmissionForm(forms.ModelForm):
    choices_text = forms.CharField(
        required=False,
        label="Choices (For Predictive Choice)",
        help_text="Comma separated (e.g., Brazil, France, Argentina).",
        widget=forms.TextInput(attrs={'placeholder': 'Option A, Option B...'})
    )

    context = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Provide enough context so the AI and the community understand exactly what is being predicted or debated.'}),
        min_length=50,
        help_text="Minimum 50 characters. Explain the background of this question."
    )

    class Meta:
        model = Question
        fields = ['text', 'context', 'question_type', 'resolution_date']
        widgets = {
            'text': forms.TextInput(attrs={'placeholder': 'e.g., Will SpaceX land an uncrewed Starship on Mars by Dec 31, 2026?'}),
            'resolution_date': forms.DateTimeInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        q_type = cleaned_data.get('question_type')
        choices_text = cleaned_data.get('choices_text', '')

        if q_type == 'PREDICTIVE_CHOICE':
            if not choices_text.strip():
                self.add_error('choices_text', 'Specific choices are required for Predictive Choice questions.')
            else:
                cleaned_data['choices'] = [c.strip() for c in choices_text.split(',') if c.strip()]
        else:
            cleaned_data['choices'] = []
            
        return cleaned_data