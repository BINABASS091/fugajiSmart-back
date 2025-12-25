"""
API documentation extensions for drf-spectacular.
This file contains schema extensions and examples for better API documentation.
"""
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiExample,
    OpenApiParameter, OpenApiResponse, OpenApiTypes
)
from rest_framework import status

# Common response examples
AUTH_ERROR_RESPONSE = {
    status.HTTP_401_UNAUTHORIZED: {
        'type': 'object',
        'properties': {
            'detail': {'type': 'string', 'example': 'Authentication credentials were not provided.'}
        }
    },
    status.HTTP_403_FORBIDDEN: {
        'type': 'object',
        'properties': {
            'detail': {'type': 'string', 'example': 'You do not have permission to perform this action.'}
        }
    }
}

# Common parameters
PAGINATION_PARAMETERS = [
    OpenApiParameter(
        name='page',
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description='A page number within the paginated result set.',
        required=False
    ),
    OpenApiParameter(
        name='page_size',
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description='Number of results to return per page.',
        required=False
    ),
]

# Common response schemas
USER_EXAMPLE = {
    'id': 1,
    'email': 'farmer@example.com',
    'role': 'FARMER',
    'phone': '+254712345678',
    'farmer_profile': {
        'business_name': 'Kuku Farm Ltd',
        'location': 'Nairobi, Kenya',
        'experience_years': 5,
        'verification_status': 'VERIFIED'
    }
}

# Common decorators
def extend_schema_auth(tags=None, responses=None, **kwargs):
    """Decorator for authentication endpoints with common responses.
    
    Args:
        tags: List of tags for the endpoint
        responses: Custom responses to merge with default error responses
        **kwargs: Additional arguments to pass to extend_schema
    """
    if tags is None:
        tags = ['Authentication']
    
    default_responses = {
        status.HTTP_400_BAD_REQUEST: {
            'type': 'object',
            'properties': {
                'field_name': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'example': ['This field is required.']
                }
            }
        },
        **AUTH_ERROR_RESPONSE
    }
    
    # Merge custom responses with default ones if provided
    if responses:
        default_responses.update(responses)
    
    return extend_schema(
        tags=tags,
        responses=default_responses,
        **{k: v for k, v in kwargs.items() if k != 'responses'}
    )

def extend_schema_list(tags=None, **kwargs):
    """Decorator for list endpoints with pagination."""
    return extend_schema(
        parameters=PAGINATION_PARAMETERS,
        tags=tags,
        **kwargs
    )

# View-specific schemas
LOGIN_EXAMPLES = [
    OpenApiExample(
        'Login Success',
        value={
            'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
            'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
            'user': USER_EXAMPLE
        },
        response_only=True,
        status_codes=['200']
    ),
    OpenApiExample(
        'Login Failed',
        value={
            'detail': 'No active account found with the given credentials'
        },
        response_only=True,
        status_codes=['401']
    )
]

REGISTER_EXAMPLES = [
    OpenApiExample(
        'Registration Success',
        value={
            'email': 'newfarmer@example.com',
            'role': 'FARMER',
            'phone': '+254712345679',
            'password': 'securepassword123',
            'password2': 'securepassword123'
        },
        request_only=True
    )
]

FARM_EXAMPLES = [
    OpenApiExample(
        'Farm Creation',
        value={
            'name': 'Green Valley Poultry',
            'location': 'Nairobi, Kenya',
            'size': 5.5,
            'farm_type': 'POULTRY',
            'description': 'Organic poultry farm specializing in free-range chickens'
        },
        request_only=True
    )
]
