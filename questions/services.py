import logging
import os
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from .models import HumanVote, AnonymousVote

logger = logging.getLogger(__name__)

def get_client_ip(request) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or '0.0.0.0'

def process_vote(request, question, parsed_data: dict) -> tuple[bool, str]:
    """
    Handles the creation/update of votes.
    Implements security checks, backend normalization, and audit logging.
    """
    disable_anon = os.environ.get("DISABLE_ANONYMOUS_VOTING", "False") == "True"
    
    if question.status == 'ARCHIVED':
        return False, "This question is archived and no longer accepting votes."

    if question.question_type == 'PREDICTIVE_CHOICE':
        forecast = parsed_data.get('complex_forecast', [])
        current_sum = sum(float(item['confidence']) for item in forecast)
        
        if current_sum > 100.1:
            return False, "Total confidence cannot exceed 100%."
        
        if current_sum < 100.0:
            remainder = round(100.0 - current_sum, 2)
            other_entry = next((i for i in forecast if i['choice'].lower() == 'other'), None)
            if other_entry:
                other_entry['confidence'] = round(other_entry['confidence'] + remainder, 2)
            else:
                forecast.append({"choice": "Other", "confidence": remainder})
        
        parsed_data['complex_forecast'] = forecast

    try:
        ip = get_client_ip(request)
        if request.user.is_authenticated:
            vote, created = HumanVote.objects.update_or_create(
                user=request.user,
                question=question,
                defaults=parsed_data
            )
            identifier = f"USER:{request.user.username}"
        else:
            if disable_anon:
                return False, "Anonymous voting is disabled. Please sign in."

            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key
            
            parsed_data['ip_address'] = ip
            parsed_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:250]
            
            vote, created = AnonymousVote.objects.update_or_create(
                session_key=session_key,
                question=question,
                defaults=parsed_data
            )
            identifier = f"ANON:{session_key[:8]}"
            
        action = "CREATED" if created else "UPDATED"
        logger.info(f"VOTE_SUCCESS | {action} | {identifier} | IP:{ip} | Q:{question.slug}")
        return True, "Your view has been successfully recorded!"
        
    except ValidationError as e:
        msg = e.message_dict if hasattr(e, 'message_dict') else str(e)
        logger.warning(f"VOTE_VAL_FAIL | Q:{question.slug} | {identifier} | ERR:{msg}")
        return False, f"Validation Error: {msg}"
        
    except Exception as e:
        logger.exception(f"VOTE_CRITICAL | Q:{question.slug}")
        return False, "An unexpected internal error occurred."