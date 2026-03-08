import json
from urllib import request
from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import login,logout,authenticate
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Avg
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from .models import SymptomLog, HealthProfile, AIAnalysis
from .services.openrouter_ai import analyze_symptoms_with_ai
from .models import *

User = get_user_model()

def signup(request):
    if request.method == "POST":
        data = request.POST
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        confirmpassword = data.get('confirmpassword')

        if password != confirmpassword:
            messages.error(request, "Password do not match!")
            return redirect('sign-up')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists!')
            return redirect('sign-up')

        # User create ho raha hai
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # ✅ Success message dikhao
        messages.success(request, "Registration successful! Please sign in.")
        return redirect('sign-in') 

    return render(request, 'guidence/split/sign-up.html')


def signin(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            # Role-based redirection
            if user.is_staff or user.is_superuser:
                return redirect('admin_dashboard')
            else:
                return redirect('user_dashboard')
        else:
            messages.error(request, "Invalid email or password")
            return redirect('sign-in')

    return render(request, 'guidence/split/sign-in.html')

@staff_member_required
def admin_dashboard(request):
    total_users = CustomUser.objects.filter(is_staff=False).count()
    total_admins = CustomUser.objects.filter(is_staff=True).count()
    total_symptoms = SymptomLog.objects.count()
    total_illnesses = IllnessInfo.objects.count()

    # Chart ke center mein dikhane ke liye grand total
    grand_total = total_users + total_admins + total_symptoms

    recent_appointments = SymptomLog.objects.select_related('user').all().order_by('-entry_date')

    patient_groups = (
        SymptomLog.objects.values('symptom_name')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    context = {
        'total_users': total_users,
        'total_admins': total_admins,
        'total_symptoms': total_symptoms,
        'total_illnesses': total_illnesses,
        'grand_total': grand_total,  # Naya variable
        'recent_appointments': recent_appointments,
        'patient_groups': patient_groups,
    }

    return render(request, 'guidence/split/admin_dashboard.html', context)

@staff_member_required
def admin_patients(request):
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        action = request.POST.get("action")

        if action == "delete" and user_id:
            try:
                user_to_delete = CustomUser.objects.get(id=user_id)
                if user_to_delete.is_superuser:
                    messages.error(request, "Cannot delete an admin user.")
                else:
                    user_to_delete.delete()
                    messages.success(request, f"User '{user_to_delete.username}' deleted successfully.")
            except CustomUser.DoesNotExist:
                messages.error(request, "User not found.")
        
        return redirect("admin_patients")  # reload the page

    # GET request - show all users
    users = CustomUser.objects.filter(is_superuser=False).order_by("-date_joined")
    context = {"users": users}
    return render(request, "guidence/split/admin_patients.html", context)

@login_required
def user_dashboard(request):
    # Get or create health profile
    profile, created = HealthProfile.objects.get_or_create(user=request.user)
    
    # Get latest symptoms with related data
    latest_symptoms = SymptomLog.objects.filter(user=request.user).order_by('-entry_date')[:5]
    
    # Get latest AI analysis
    latest_log = SymptomLog.objects.filter(user=request.user).order_by('-id').first()
    analysis = None
    if latest_log:
        analysis = getattr(latest_log, 'ai_analysis', None) or AIAnalysis.objects.filter(symptom_log=latest_log).first()
    
    # Calculate health statistics
    total_symptoms = SymptomLog.objects.filter(user=request.user).count()
    avg_severity = SymptomLog.objects.filter(user=request.user).aggregate(
        avg_severity=Avg('severity')
    )['avg_severity'] or 0
    
    # Get recent analysis count
    recent_analyses = AIAnalysis.objects.filter(
        symptom_log__user=request.user
    ).count()
    
    # Calculate health score based on various factors
    health_score = 85  # Default score
    if analysis and analysis.confidence_score:
        health_score = analysis.confidence_score
    elif avg_severity > 0:
        # Calculate based on average severity (lower severity = higher score)
        health_score = max(20, 100 - (avg_severity * 10))
    
    # Get symptom trends for chart (last 7 entries)
    symptom_trends = SymptomLog.objects.filter(
        user=request.user
    ).order_by('-entry_date')[:7]
    
    # Health tips based on user data
    health_tips = []
    if avg_severity > 7:
        health_tips.append({
            'icon': 'fas fa-exclamation-triangle',
            'color': 'danger',
            'title': 'High Severity Alert',
            'message': 'Consider consulting a healthcare professional for your recent symptoms.'
        })
    elif total_symptoms == 0:
        health_tips.append({
            'icon': 'fas fa-heart',
            'color': 'success',
            'title': 'Great Health!',
            'message': 'No symptoms logged recently. Keep maintaining your healthy lifestyle!'
        })
    else:
        health_tips.append({
            'icon': 'fas fa-chart-line',
            'color': 'info',
            'title': 'Track Progress',
            'message': 'Continue monitoring your symptoms to identify patterns.'
        })
    
    # Add hydration tip
    health_tips.append({
        'icon': 'fas fa-tint',
        'color': 'primary',
        'title': 'Stay Hydrated',
        'message': 'Drink at least 8 glasses of water daily for optimal health.'
    })
    
    context = {
        'profile': profile,
        'latest_symptoms': latest_symptoms,
        'analysis': analysis,
        'total_symptoms': total_symptoms,
        'avg_severity': round(avg_severity, 1),
        'recent_analyses': recent_analyses,
        'health_score': int(health_score),
        'symptom_trends': symptom_trends,
        'health_tips': health_tips,
        'user_first_name': request.user.first_name or request.user.username,
    }
    return render(request, 'guidence/split/user_dashboard.html', context)


@login_required
def signout(request):
    logout(request)
    return render(request, 'guidence/split/sign-out.html')

@staff_member_required
def admin_profile(request):
    user = request.user

    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        profile_picture = request.FILES.get('profile_picture')

        # Update basic info
        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name

        # Update password if provided
        if password:
            user.set_password(password)
            update_session_auth_hash(request, user)

        if profile_picture:
            user.profile_picture = profile_picture
        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('admin_profile')
    return render(request, 'guidence/split/admin_profile.html', {'user': user})

@login_required
def user_profile(request):
    user = request.user

    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        profile_picture = request.FILES.get('profile_picture')

        # Update basic info
        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name

        # Update password if provided
        if password:
            user.set_password(password)
            update_session_auth_hash(request, user)

        if profile_picture:
            user.profile_picture = profile_picture
        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('user_profile')
    return render(request, 'guidence/split/user_profile.html', {'user': user})

@login_required
def health_profile(request):
    # 🔹 Get or create HealthProfile for logged-in user
    health_profile, created = HealthProfile.objects.get_or_create(user=request.user)

    # ---------------- POST REQUEST ----------------
    if request.method == "POST":

        # -------- DELETE CASE --------
        if "delete_profile" in request.POST:
            health_profile.delete()
            messages.success(request, "Health profile deleted successfully.")
            return redirect("health_profile")  # Ya jis page pe user ko bhejna ho

        # -------- ADD / UPDATE CASE --------
        gender = request.POST.get("gender")
        blood = request.POST.get("blood")  # Old + new mapping
        height = request.POST.get("height")
        weight = request.POST.get("weight")
        conditions = request.POST.get("conditions")
        allergies = request.POST.get("allergies")
        blood_pressure = request.POST.get("blood_pressure")
        last_checkup_date = request.POST.get("last_checkup_date")

        # SAVE DATA
        health_profile.gender = gender
        health_profile.blood_group = blood  # Old field
        health_profile.blood_type = blood   # New field
        health_profile.height = height if height else None
        health_profile.weight = weight if weight else None
        health_profile.known_conditions = conditions
        health_profile.allergies = allergies
        health_profile.blood_pressure = blood_pressure
        if last_checkup_date:
            health_profile.last_checkup_date = last_checkup_date

        health_profile.save()
        messages.success(request, "Health profile saved successfully.")
        return redirect("health_profile")

    # ---------------- GET REQUEST ----------------
    context = {
        "health_profile": health_profile,
        "is_new": created
    }
    return render(request, "guidence/split/health_profile.html", context)


@login_required
def add_symptom(request, pk=None):
    """
    Add & Update Symptom (Same View) + AI Analysis
    """
    symptom = None

    if pk:
        symptom = get_object_or_404(SymptomLog, pk=pk, user=request.user)

    if request.method == "POST":
        if symptom:
            # UPDATE
            symptom.symptom_name = request.POST.get("symptom_name")
            symptom.body_part = request.POST.get("body_part")
            symptom.severity = request.POST.get("severity")
            symptom.duration = request.POST.get("duration")
            symptom.started_when = request.POST.get("started_when")
            symptom.description = request.POST.get("description")
            symptom.save()

            messages.success(request, "Symptom updated successfully")

        else:
            # CREATE
            symptom = SymptomLog.objects.create(
                user=request.user,
                symptom_name=request.POST.get("symptom_name"),
                body_part=request.POST.get("body_part"),
                severity=request.POST.get("severity"),
                duration=request.POST.get("duration"),
                started_when=request.POST.get("started_when"),
                description=request.POST.get("description"),
            )

            # 🔥 AI CALL HERE
            symptom_text = f"Symptom: {symptom.symptom_name}, Body Part: {symptom.body_part}"
            ai_text = analyze_symptoms_with_ai(symptom_text)

            # 🔥 SAVE AI RESULT
            AIAnalysis.objects.create(
            symptom_log=symptom,
            possible_illnesses=[ai_text],
            confidence_score=70,
            urgency_level="self_monitor"
            )
            messages.success(request, "Symptom added & AI guidance generated")
        return redirect('user_symptom_history')

    return render(request, "guidence/split/add_symptom.html", {
        "symptom": symptom
    })

@login_required
def user_symptom_history(request):
    symptoms = SymptomLog.objects.filter(user=request.user).order_by("-entry_date")
    return render(request, "guidence/split/user_symptom_history.html", {
        "symptoms": symptoms
    })


@login_required
def delete_symptom(request, pk):
    symptom = get_object_or_404(SymptomLog, pk=pk, user=request.user)
    symptom.delete()
    messages.success(request, "Symptom deleted successfully")
    return redirect("user_symptom_history")

@staff_member_required
def admin_symptom_history(request):
    symptoms = SymptomLog.objects.exclude(user__is_staff=True).order_by("-entry_date")
    
    # Delete Logic
    if request.method == "POST" and "delete_id" in request.POST:
        s_id = request.POST.get("delete_id")
        log = get_object_or_404(SymptomLog, id=s_id)
        log.delete()
        messages.success(request, "Symptom record deleted successfully.")
        return redirect("admin_symptom_history")

    return render(request, "guidence/split/admin_symptom_history.html", {"symptoms": symptoms})

@staff_member_required
def admin_illness_information(request):
    if request.method == "POST":
        action = request.POST.get("action")
        illness_id = request.POST.get("illness_id")

        if action == "add":
            try:
                IllnessInfo.objects.create(
                    name=request.POST.get("name"),
                    category=request.POST.get("category"),
                    description=request.POST.get("description"),
                    primary_symptoms=request.POST.get("primary_symptoms"),
                    severity=request.POST.get("severity")
                )
                messages.success(request, "New illness information added successfully!")
            except IntegrityError:
                messages.error(request, f"Error: '{request.POST.get('name')}' already exists. please use a diffrent name.")

        elif action == "update":
            obj = get_object_or_404(IllnessInfo, id=illness_id)
            try:
                obj.name = request.POST.get("name")
                obj.category = request.POST.get("category")
                obj.description = request.POST.get("description")
                obj.primary_symptoms = request.POST.get("primary_symptoms")
                obj.severity = request.POST.get("severity")
                obj.save()
                messages.info(request, f"Details for {obj.name} updated.")
            except IntegrityError:
                messages.error(request, "Update failed: Please choose a diffrent name, this on ealreafy exists.")

        elif action == "delete":
            obj = get_object_or_404(IllnessInfo, id=illness_id)
            obj.delete()
            messages.error(request, "Illness record deleted.")

        return redirect("admin_illness_information")

    selected_category = request.GET.get("category", "")
    
    if selected_category:
        illnesses = IllnessInfo.objects.filter(category=selected_category)
    else:
        illnesses = IllnessInfo.objects.all()

    context = {
        "illnesses": illnesses,
        "categories": IllnessInfo.CATEGORIES, 
        "severity_choices": IllnessInfo.SEVERITY_LEVELS,  
        "selected_category": selected_category,
    }

    return render(request, "guidence/split/admin_illness_information.html", context)

@login_required
def user_illness_information(request):
    selected_category = request.GET.get("category", "")
    illnesses = IllnessInfo.objects.all()

    if selected_category:
        illnesses = illnesses.filter(category=selected_category)

    categories = IllnessInfo.CATEGORIES

    return render(
        request,
        "guidence/split/user_illness_information.html",
        {
            "illnesses": illnesses,
            "categories": categories,
            "selected_category": selected_category,
        }
    )

    
@login_required
def user_run_ai_analysis(request, symptom_id):
    symptom = get_object_or_404(SymptomLog, id=symptom_id, user=request.user)

    symptom_text = (
        f"Symptom: {symptom.symptom_name}, Body Part: {symptom.body_part}, "
        f"Severity: {symptom.get_severity_display()}, Duration: {symptom.get_duration_display()}. "
        f"Respond ONLY in valid JSON format with these exact keys: "
        f'"illnesses" (list of objects with "name" & "match"), '
        f'"confidence" (number), '
        f'"urgency" (one of: self_monitor, schedule_appointment, urgent_care, emergency), '
        f'"guidance" (string with health advice).'
    )

    ai_response = analyze_symptoms_with_ai(symptom_text)
    
    raw_content = ""
    is_error = False

    # FIX: Using .get() to prevent KeyError 'choices'
    if isinstance(ai_response, dict):
        if "error" in ai_response:
            is_error = True
            # Extract specific error message if available
            err_msg = ai_response["error"].get("message", "Unknown API error")
            raw_content = f"API Error: {err_msg}"
        else:
            choices = ai_response.get("choices")
            if choices and isinstance(choices, list) and len(choices) > 0:
                raw_content = choices[0].get("message", {}).get("content", "")
            else:
                # If 'choices' is missing or empty
                raw_content = str(ai_response)
                # If the response looks like an error string
                if "error" in raw_content.lower():
                    is_error = True
    else:
        raw_content = str(ai_response)

    print("AI RESPONSE DEBUG:", raw_content)

    data = {}
    if not is_error and raw_content:
        # Robust extraction of JSON
        if "```json" in raw_content:
            try:
                raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            except IndexError:
                pass
        elif "```" in raw_content:
            try:
                raw_content = raw_content.split("```")[1].split("```")[0].strip()
            except IndexError:
                pass

        try:
            data = json.loads(raw_content)
        except Exception:
            # If standard JSON parsing fails, try to find { }
            match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except:
                    pass

    illnesses = data.get("illnesses", [])
    if not isinstance(illnesses, list):
        illnesses = []

    guidance_text = data.get("guidance") or raw_content

    if data.get("guidance") and isinstance(illnesses, list):
        # Only append if guidance isn't already there
        if not any(item.get('type') == 'guidance' for item in illnesses):
            illnesses.append({
                "type": "guidance",
                "text": data.get("guidance")
            })

    analysis, _ = AIAnalysis.objects.update_or_create(
        symptom_log=symptom,
        defaults={
            "possible_illnesses": illnesses,
            "confidence_score": data.get("confidence") or 0,
            "urgency_level": data.get("urgency") or "self_monitor",
        }
    )

    return render(request, "guidence/split/user_ai_analysis.html", {
        "symptom": symptom,
        "analysis": analysis,
        "ai_text": guidance_text,
        "is_error": is_error,
    })

@staff_member_required
def admin_ai_analysis(request,symptom_id=None):
    reports = SymptomLog.objects.filter(user__is_staff=False).select_related('ai_analysis', 'user').order_by('-id')

    for r in reports:
        analysis = getattr(r, 'ai_analysis', None)
        r.ai_text = "No guidance found"
        r.possible_illnesses_list = []
        r.disp_confidence = 0
        r.disp_urgency = "N/A"

        if analysis:
            r.disp_confidence = analysis.confidence_score
            r.disp_urgency = analysis.get_urgency_level_display()

            data = analysis.possible_illnesses
            guidance_found = False

            # If data is list
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        if item.get("type") == "guidance":
                            r.ai_text = item.get("text", "No guidance found")
                            guidance_found = True
                        else:
                            # Treat other dicts as possible illnesses
                            name = item.get("name") or item.get("illness_name")
                            if name:
                                r.possible_illnesses_list.append(name)
            # If data is dict
            elif isinstance(data, dict):
                r.ai_text = data.get("text") or data.get("guidance") or "No guidance found"

            if not guidance_found and not r.ai_text:
                r.ai_text = "No guidance found"

    # Delete logic
    if request.method == "POST" and request.POST.get('action') == "delete":
        s_id = request.POST.get('symptom_id')
        SymptomLog.objects.filter(id=s_id).delete()
        return redirect('admin_latest_ai_analysis')

    return render(request, "guidence/split/admin_ai_analysis.html", {"reports": reports})


@login_required
def user_ai_analysis(request, symptom_id):
    symptom = get_object_or_404(SymptomLog, id=symptom_id, user=request.user)

    symptom_text = (
        f"Symptom: {symptom.symptom_name}, Body Part: {symptom.body_part}, "
        f"Severity: {symptom.get_severity_display()}, Duration: {symptom.get_duration_display()}. "
        f"Respond ONLY in JSON with these keys: "
        f"illnesses (list of objects with name & match), "
        f"confidence (number), urgency (one of: self_monitor, schedule_appointment, urgent_care, emergency), "
        f"guidance (string with health advice)."
    )

    ai_response = analyze_symptoms_with_ai(symptom_text)
    raw_content = ai_response["choices"][0]["message"]["content"]

    if "```json" in raw_content:
        raw_content = raw_content.split("```json")[1].split("```")[0].strip()

    try:
        data = json.loads(raw_content)
    except Exception:
        data = {}

    illnesses = data.get("illnesses") or []

    # 👉 Yahin AI ka real guidance add ho raha hai (NO static text)
    guidance_text = data.get("guidance")
    if guidance_text:
        illnesses.append({
            "type": "guidance",
            "text": guidance_text
        })

    analysis, _ = AIAnalysis.objects.update_or_create(
        symptom_log=symptom,
        defaults={
            "possible_illnesses": illnesses,   # 👈 yahin guidance bhi save
            "confidence_score": data.get("confidence") or 0,
            "urgency_level": data.get("urgency") or "self_monitor",
        }
    )

    return render(request, "guidence/split/user_ai_analysis.html", {
        "symptom": symptom,
        "analysis": analysis,
        "ai_text": guidance_text,   # frontend display
    })


@staff_member_required
def admin_latest_ai_analysis(request):
    latest_log = SymptomLog.objects.filter(user__is_staff=False).order_by('-id').first()
    
    if latest_log:
        return redirect('admin_ai_analysis', symptom_id=latest_log.id) 
    messages.info(request, "No patient analysis reports found.")
    return redirect('admin_dashboard')

@login_required
def user_latest_ai_analysis(request):
    latest_log = SymptomLog.objects.filter(user=request.user).order_by('-id').first()
    if latest_log:
        return redirect('user_ai_analysis', symptom_id=latest_log.id) 
    return redirect('add_symptom')


def forgotpassword(request):
    if request.method == "POST":
        email = request.POST.get('email')
        try:
            user = CustomUser.objects.get(email=email)
            
            # Generate token
            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Create reset link
            reset_link = f"{request.build_absolute_uri('/reset-password/')}?uid={uid}&token={token}"
            
            # Send email
            subject = "Password Reset Request"
            message = f"""
            Hi {user.username},
            
            You requested to reset your password. Click on the link below to reset it:
            
            {reset_link}
            
            If you didn't request this, please ignore this email.
            
            Best regards,
            SymptoGuide AI Team
            """
            
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            
            messages.success(request, "Password reset link sent to your email. Please check your inbox.")
            return redirect('sign-in')
            
        except CustomUser.DoesNotExist:
            messages.error(request, "Email address not found in our system.")
            return render(request, 'guidence/split/forgot-password.html')
    
    return render(request, 'guidence/split/forgot-password.html')


def reset_password(request):
    if request.method == "POST":
        uid = request.POST.get('uid')
        token = request.POST.get('token')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirmPassword')
        
        try:
            # Decode uid
            user_id = force_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(pk=user_id)
            
            # Verify token
            token_generator = PasswordResetTokenGenerator()
            if not token_generator.check_token(user, token):
                messages.error(request, "Invalid or expired reset link.")
                return render(request, 'guidence/split/reset-password.html')
            
            # Validate passwords
            if password != confirm_password:
                messages.error(request, "Passwords do not match!")
                return render(request, 'guidence/split/reset-password.html', {
                    'uid': uid,
                    'token': token
                })
            
            if len(password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                return render(request, 'guidence/split/reset-password.html', {
                    'uid': uid,
                    'token': token
                })
            
            # Set new password
            user.set_password(password)
            user.save()
            
            messages.success(request, "Password reset successfully! You can now sign in with your new password.")
            return redirect('sign-in')
            
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            messages.error(request, "Invalid reset link.")
            return render(request, 'guidence/split/reset-password.html')
    
    # GET request - display the reset form
    uid = request.GET.get('uid')
    token = request.GET.get('token')
    
    if not uid or not token:
        messages.error(request, "Invalid reset link.")
        return redirect('forgot_password')
    
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = CustomUser.objects.get(pk=user_id)
        
        # Verify token
        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, token):
            messages.error(request, "Invalid or expired reset link.")
            return redirect('forgot_password')
        
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        messages.error(request, "Invalid reset link.")
        return redirect('forgot_password')
    
    return render(request, 'guidence/split/reset-password.html', {
        'uid': uid,
        'token': token
    })



def home(request):
    return render(request,'guidence/split/sign-in..html')









































































