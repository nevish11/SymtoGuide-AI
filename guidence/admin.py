from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser,
    HealthProfile,
    SymptomLog,
    IllnessInfo,
    AIAnalysis,
)

# -------------------------
# Custom User Admin
# -------------------------
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    list_display = ('email', 'username', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')

    ordering = ('email',)
    search_fields = ('email', 'username')

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Profile', {'fields': ('profile_picture',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )

# -------------------------
# Health Profile Admin
# -------------------------
@admin.register(HealthProfile)
class HealthProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'blood_type', 'height', 'weight')
    search_fields = ('user__email', 'user__username')

# -------------------------
# Symptom Log Admin
# -------------------------
@admin.register(SymptomLog)
class SymptomLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'symptom_name', 'body_part', 'severity', 'entry_date')
    list_filter = ('severity', 'body_part')
    search_fields = ('symptom_name', 'user__email')

# -------------------------
# Illness Info Admin
# -------------------------
@admin.register(IllnessInfo)
class IllnessInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'severity')
    search_fields = ('name', 'primary_symptoms')
    list_filter = ('category', 'severity')

# -------------------------
# AI Analysis Admin
# -------------------------
@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ('symptom_log', 'confidence_score', 'urgency_level', 'analysis_date')
    list_filter = ('urgency_level',)

# -------------------------
# Symptom Pattern Admin
# -------------------------

