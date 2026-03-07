from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

# Custom User Model
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email

# Health Profile Model
class HealthProfile(models.Model):
    BLOOD_TYPE_CHOICES = (
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    )
    
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='health_profile')
    
    # Essential Health Info
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True)
    blood_type = models.CharField(max_length=10, choices=BLOOD_TYPE_CHOICES, blank=True, null=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, help_text="Height in cm", blank=True, null=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="Weight in kg", blank=True, null=True)
    
    # Medical Conditions (simplified)
    known_conditions = models.TextField(blank=True, null=True, help_text="Known medical conditions")
    allergies = models.TextField(blank=True, null=True, help_text="Known allergies")
    
    # Current Vitals
    blood_pressure = models.CharField(max_length=20, blank=True, null=True, help_text="Format: 120/80")
    last_checkup_date = models.DateField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Health Profile - {self.user.username}"

# Symptom Log Model (Core Model)
class SymptomLog(models.Model):
    SEVERITY_CHOICES = (
        (1, 'Mild'),
        (2, 'Moderate'),
        (3, 'Severe'),
    )
    
    BODY_PARTS = (
        ('head', 'Head (Headache, Dizziness)'),
        ('eyes', 'Eyes (Vision, Pain)'),
        ('ears', 'Ears (Hearing, Pain)'),
        ('nose', 'Nose (Congestion, Bleeding)'),
        ('mouth', 'Mouth/Throat (Sore throat, Swallowing)'),
        ('chest', 'Chest (Pain, Breathing)'),
        ('abdomen', 'Abdomen (Stomach pain, Digestion)'),
        ('back', 'Back (Pain, Stiffness)'),
        ('arms', 'Arms/Hands (Pain, Numbness)'),
        ('legs', 'Legs/Feet (Pain, Swelling)'),
        ('skin', 'Skin (Rash, Itching)'),
        ('urinary', 'Urinary (Pain, Frequency)'),
        ('general', 'General (Fever, Fatigue)'),
    )
    
    DURATION_CHOICES = (
        ('hours', 'Hours (Less than 24 hours)'),
        ('days', 'Days (1-7 days)'),
        ('weeks', 'Weeks (1-4 weeks)'),
        ('months', 'Months (More than 1 month)'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='symptom_logs')
    symptom_name = models.CharField(max_length=200, help_text="Describe your symptom")
    body_part = models.CharField(max_length=50, choices=BODY_PARTS)
    severity = models.IntegerField(choices=SEVERITY_CHOICES, default=2)
    
    # Duration & Timing
    duration = models.CharField(max_length=20, choices=DURATION_CHOICES, default='days')
    started_when = models.DateTimeField(help_text="When did this symptom start?")
    
    # Symptom Details
    description = models.TextField(blank=True, null=True, help_text="Describe in your own words")
    entry_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.symptom_name} ({self.get_severity_display()})"

# Illness Information Model (Symptom-focused)
class IllnessInfo(models.Model):
    CATEGORIES = (
        ('respiratory', 'Respiratory (Lungs, Breathing)'),
        ('cardiovascular', 'Heart & Circulation'),
        ('gastrointestinal', 'Digestive System'),
        ('neurological', 'Brain & Nerves'),
        ('musculoskeletal', 'Muscles & Bones'),
        ('skin', 'Skin Conditions'),
        ('infectious', 'Infectious Diseases'),
        ('endocrine', 'Hormones & Metabolism'),
        ('mental_health', 'Mental Health'),
        ('other', 'Other'),
    )
    
    SEVERITY_LEVELS = (
        ('self_care', 'Usually Self-Care'),
        ('doctor', 'See a Doctor'),
        ('urgent', 'Urgent Care Needed'),
        ('emergency', 'Medical Emergency'),
    )
    
    name = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=100, choices=CATEGORIES)
    
    # What it is
    description = models.TextField(help_text="Brief explanation of what this illness is")
    
    # Key Symptoms (What users feel)
    primary_symptoms = models.TextField(help_text="Main symptoms people experience (comma-separated)")
    
    # Severity & Urgency
    severity = models.CharField(max_length=50, choices=SEVERITY_LEVELS)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

# AI Analysis Model (Symptom Analysis Only)
class AIAnalysis(models.Model):
    symptom_log = models.OneToOneField(SymptomLog, on_delete=models.CASCADE, related_name='ai_analysis')
    analysis_date = models.DateTimeField(auto_now_add=True)
    
    # Analysis Results
    possible_illnesses = models.JSONField(default=list, help_text="List of possible illnesses with match scores")
    confidence_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Priority & Urgency
    urgency_level = models.CharField(max_length=50, choices=[
        ('self_monitor', 'Monitor at Home'),
        ('schedule_appointment', 'Schedule Doctor Visit'),
        ('urgent_care', 'Consider Urgent Care'),
        ('emergency', 'Seek Emergency Care'),
    ])
    
    def __str__(self):
        return f"Symptom Analysis - {self.symptom_log.user.username}"

