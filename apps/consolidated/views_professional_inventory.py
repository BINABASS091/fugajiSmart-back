from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Q, F, FloatField, Count, Avg
from django.utils import timezone
from datetime import date, timedelta
import json

from apps.consolidated.models import InventoryItem, Batch, Farm, InventoryTransaction
from apps.consolidated.serializers import InventoryItemSerializer, InventoryTransactionSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def batch_inventory_summary(request, batch_id):
    """
    Get comprehensive inventory summary for a specific batch
    Includes all inventory items assigned to the batch with professional metrics
    """
    try:
        batch = get_object_or_404(Batch, id=batch_id, farm__farmer=request.user.farmerprofile)
        
        # Get all inventory items for this batch
        inventory_items = InventoryItem.objects.filter(batch=batch)
        
        # Calculate comprehensive metrics
        total_inventory_value = inventory_items.aggregate(
            total_cost=Sum(F('quantity') * F('cost_per_unit'), output_field=FloatField()),
            total_market_value=Sum(
                F('quantity') * F('market_price_per_unit'), 
                output_field=FloatField()
            )
        )
        
        # Category-wise breakdown
        category_breakdown = inventory_items.values('category').annotate(
            item_count=Count('id'),
            total_quantity=Sum('quantity'),
            total_cost=Sum(F('quantity') * F('cost_per_unit'), output_field=FloatField()),
            avg_cost_per_unit=Avg('cost_per_unit')
        ).order_by('-total_cost')
        
        # Status breakdown
        status_counts = {}
        for item in inventory_items:
            status = item.get_inventory_status()
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Expiry analysis
        expiry_analysis = {
            'expired': inventory_items.filter(is_expired=True).count(),
            'near_expiry': inventory_items.filter(is_near_expiry=True).count(),
            'adequate_shelf_life': inventory_items.filter(
                expiry_date__gt=date.today() + timedelta(days=30)
            ).count()
        }
        
        # Reorder analysis
        reorder_analysis = {
            'needs_reorder': inventory_items.filter(should_reorder=True).count(),
            'low_stock': inventory_items.filter(
                quantity__lte=F('reorder_level')
            ).count(),
            'adequate_stock': inventory_items.filter(
                quantity__gt=F('reorder_level')
            ).count()
        }
        
        # Recent transactions
        recent_transactions = InventoryTransaction.objects.filter(
            item__in=inventory_items
        ).order_by('-created_at')[:10]
        
        response_data = {
            'batch_info': {
                'id': str(batch.id),
                'batch_number': batch.batch_number,
                'breed': batch.breed,
                'quantity': batch.quantity,
                'status': batch.status,
                'current_age_days': batch.current_age_days
            },
            'inventory_summary': {
                'total_items': inventory_items.count(),
                'total_cost': total_inventory_value['total_cost'] or 0,
                'total_market_value': total_inventory_value['total_market_value'] or 0,
                'category_breakdown': list(category_breakdown),
                'status_counts': status_counts,
                'expiry_analysis': expiry_analysis,
                'reorder_analysis': reorder_analysis
            },
            'inventory_items': InventoryItemSerializer(inventory_items, many=True).data,
            'recent_transactions': InventoryTransactionSerializer(recent_transactions, many=True).data
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def professional_inventory_analytics(request):
    """
    Professional inventory analytics with (s,S) policy optimization
    Based on research methodology for poultry feed inventory management
    """
    try:
        farmer = request.user.farmerprofile
        
        # Get all inventory items for the farmer
        inventory_items = InventoryItem.objects.filter(farmer=farmer)
        
        # Calculate key metrics
        total_items = inventory_items.count()
        total_investment = sum(item.calculate_total_cost() for item in inventory_items)
        total_market_value = sum(item.calculate_market_value() for item in inventory_items)
        
        # Category analysis
        category_metrics = {}
        for category_code, category_name in InventoryItem.CATEGORY_CHOICES:
            category_items = inventory_items.filter(category=category_code)
            if category_items.exists():
                category_metrics[category_code] = {
                    'name': category_name,
                    'item_count': category_items.count(),
                    'total_cost': sum(item.calculate_total_cost() for item in category_items),
                    'market_value': sum(item.calculate_market_value() for item in category_items),
                    'avg_cost_per_unit': category_items.aggregate(
                        avg_cost=Avg('cost_per_unit')
                    )['avg_cost'] or 0
                }
        
        # Feed stage analysis (for feed items)
        feed_stage_analysis = {}
        feed_items = inventory_items.filter(category='FEED')
        for stage_code, stage_name in [
            ('STARTER', 'Starter Feed (1-18 days)'),
            ('GROWER', 'Grower Feed (19-40 days)'),
            ('FINISHER', 'Finisher Feed (40+ days)'),
            ('LAYER', 'Layer Feed'),
            ('BREEDER', 'Breeder Feed')
        ]:
            stage_items = feed_items.filter(feed_stage=stage_code)
            if stage_items.exists():
                feed_stage_analysis[stage_code] = {
                    'name': stage_name,
                    'item_count': stage_items.count(),
                    'total_quantity': stage_items.aggregate(total=Sum('quantity'))['total'] or 0,
                    'total_cost': sum(item.calculate_total_cost() for item in stage_items)
                }
        
        # Quality analysis
        quality_analysis = {}
        for quality_code, quality_name in [
            ('PREMIUM', 'Premium'),
            ('STANDARD', 'Standard'),
            ('ECONOMY', 'Economy')
        ]:
            quality_items = inventory_items.filter(quality_grade=quality_code)
            if quality_items.exists():
                quality_analysis[quality_code] = {
                    'name': quality_name,
                    'item_count': quality_items.count(),
                    'total_value': sum(item.calculate_market_value() for item in quality_items),
                    'percentage': (quality_items.count() / total_items * 100) if total_items > 0 else 0
                }
        
        # Inventory optimization recommendations
        recommendations = []
        
        # Check for items needing reorder
        reorder_items = inventory_items.filter(should_reorder=True)
        if reorder_items.exists():
            recommendations.append({
                'type': 'REORDER_REQUIRED',
                'priority': 'HIGH',
                'message': f'{reorder_items.count()} items need immediate reordering',
                'items': [
                    {
                        'name': item.name,
                        'current_quantity': float(item.quantity),
                        'reorder_point': float(item.reorder_point) if item.reorder_point else float(item.reorder_level),
                        'suggested_order': item.calculate_order_quantity()
                    }
                    for item in reorder_items[:5]  # Top 5 items
                ]
            })
        
        # Check for near expiry items
        near_expiry_items = inventory_items.filter(is_near_expiry=True)
        if near_expiry_items.exists():
            recommendations.append({
                'type': 'NEAR_EXPIRY',
                'priority': 'MEDIUM',
                'message': f'{near_expiry_items.count()} items are near expiry',
                'items': [
                    {
                        'name': item.name,
                        'days_to_expiry': item.get_days_to_expiry(),
                        'quantity': float(item.quantity)
                    }
                    for item in near_expiry_items[:5]
                ]
            })
        
        # Service level analysis
        service_level_analysis = {}
        for item in inventory_items.filter(service_level_target__isnull=False):
            target = float(item.service_level_target)
            current_stock_ratio = float(item.quantity) / float(item.reorder_point) if item.reorder_point else 1.0
            service_level_analysis[str(item.id)] = {
                'item_name': item.name,
                'target_service_level': target,
                'current_stock_ratio': current_stock_ratio,
                'service_level_met': current_stock_ratio >= (target / 100)
            }
        
        response_data = {
            'summary': {
                'total_items': total_items,
                'total_investment': total_investment,
                'total_market_value': total_market_value,
                'potential_profit': total_market_value - total_investment
            },
            'category_metrics': category_metrics,
            'feed_stage_analysis': feed_stage_analysis,
            'quality_analysis': quality_analysis,
            'recommendations': recommendations,
            'service_level_analysis': service_level_analysis,
            'last_updated': timezone.now().isoformat()
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def optimize_inventory_policy(request):
    """
    Calculate optimal (s,S) inventory policy parameters
    Based on research methodology for minimizing total inventory costs
    """
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        demand_mean = float(data.get('demand_mean', 0))  # Average daily demand
        demand_std = float(data.get('demand_std', 0))    # Standard deviation of demand
        lead_time = int(data.get('lead_time', 2))        # Lead time in days
        ordering_cost = float(data.get('ordering_cost', 100))  # Cost per order
        holding_cost_rate = float(data.get('holding_cost_rate', 0.25))  # Annual holding cost rate
        service_level = float(data.get('service_level', 95))  # Target service level
        
        item = get_object_or_404(InventoryItem, id=item_id, farmer=request.user.farmerprofile)
        
        # Calculate optimal parameters using (s,S) policy
        # Based on research formulas from the provided paper
        
        # Convert annual holding cost rate to daily
        daily_holding_cost_rate = holding_cost_rate / 365
        
        # Calculate optimal order quantity (EOQ formula)
        if demand_mean > 0 and ordering_cost > 0 and item.cost_per_unit > 0:
            optimal_q = ((2 * ordering_cost * demand_mean) / 
                        (item.cost_per_unit * daily_holding_cost_rate)) ** 0.5
        else:
            optimal_q = 0
        
        # Calculate safety stock based on service level
        from math import sqrt
        import scipy.stats as stats
        
        # Z-score for service level
        z_score = stats.norm.ppf(service_level / 100)
        
        # Calculate safety stock
        safety_stock = z_score * demand_std * sqrt(lead_time)
        
        # Calculate reorder point (s)
        reorder_point = (demand_mean * lead_time) + safety_stock
        
        # Calculate order-up-to level (S)
        order_up_to_level = optimal_q + reorder_point
        
        # Update item with calculated parameters
        item.reorder_point = reorder_point
        item.order_up_to_level = order_up_to_level
        item.safety_stock = safety_stock
        item.lead_time_days = lead_time
        item.service_level_target = service_level
        item.save()
        
        # Calculate expected cost savings
        current_policy_cost = calculate_expected_cost(
            item.quantity, item.reorder_level, demand_mean, demand_std,
            lead_time, ordering_cost, item.cost_per_unit, daily_holding_cost_rate
        )
        
        optimal_policy_cost = calculate_expected_cost(
            order_up_to_level, reorder_point, demand_mean, demand_std,
            lead_time, ordering_cost, item.cost_per_unit, daily_holding_cost_rate
        )
        
        cost_savings = current_policy_cost - optimal_policy_cost
        cost_savings_percentage = (cost_savings / current_policy_cost * 100) if current_policy_cost > 0 else 0
        
        response_data = {
            'item_name': item.name,
            'optimal_parameters': {
                'reorder_point': reorder_point,
                'order_up_to_level': order_up_to_level,
                'safety_stock': safety_stock,
                'optimal_order_quantity': optimal_q
            },
            'cost_analysis': {
                'current_policy_cost': current_policy_cost,
                'optimal_policy_cost': optimal_policy_cost,
                'annual_cost_savings': cost_savings,
                'cost_savings_percentage': cost_savings_percentage
            },
            'parameters_used': {
                'demand_mean': demand_mean,
                'demand_std': demand_std,
                'lead_time': lead_time,
                'ordering_cost': ordering_cost,
                'holding_cost_rate': holding_cost_rate,
                'service_level': service_level
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def calculate_expected_cost(current_stock, reorder_point, demand_mean, demand_std, 
                          lead_time, ordering_cost, unit_cost, holding_cost_rate):
    """
    Calculate expected total inventory cost
    Based on research methodology
    """
    # Simplified cost calculation for demonstration
    # In practice, this would use more complex simulation models
    
    # Ordering cost (based on reorder frequency)
    if current_stock <= reorder_point:
        ordering_cost_per_period = ordering_cost
    else:
        ordering_cost_per_period = 0
    
    # Holding cost (based on average inventory)
    holding_cost_per_period = current_stock * unit_cost * holding_cost_rate
    
    # Total cost
    total_cost = ordering_cost_per_period + holding_cost_per_period
    
    return total_cost
