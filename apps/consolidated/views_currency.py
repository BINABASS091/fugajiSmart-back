from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

User = get_user_model()

@csrf_exempt
@require_http_methods(["PATCH"])
def update_currency_preference(request, *args, **kwargs):
    """
    Update user's preferred currency
    """
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        # Parse JSON data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        currency = data.get('preferred_currency')
        
        if not currency:
            return JsonResponse(
                {'error': 'Currency is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate currency choice
        valid_currencies = [choice[0] for choice in User.CURRENCY_CHOICES]
        if currency not in valid_currencies:
            return JsonResponse(
                {'error': f'Invalid currency. Must be one of: {", ".join(valid_currencies)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update user preference
        request.user.preferred_currency = currency
        request.user.save()
        
        return JsonResponse({
            'message': 'Currency preference updated successfully',
            'preferred_currency': request.user.preferred_currency
        })
        
    except Exception as e:
        return JsonResponse(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
