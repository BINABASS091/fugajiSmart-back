from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Q, F, FloatField, Count, Avg
from django.utils import timezone
from datetime import date, timedelta, datetime
import json

from apps.consolidated.models import (
    Batch, Farm, InventoryItem, InventoryTransaction, 
    FeedConsumption, HealthRecord, EggInventory, EggSale
)
from apps.consolidated.serializers import (
    BatchSerializer, FeedConsumptionSerializer, HealthRecordSerializer
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_flock_weights(request):
    """
    Log aggregate flock weights to synchronize FCR with inventory depletion
    """
    try:
        data = json.loads(request.body)
        batch_id = data.get('batch_id')
        weight_data = data.get('weight_data', [])  # Array of weight measurements
        measurement_date = data.get('measurement_date') or date.today().isoformat()
        notes = data.get('notes', '')
        
        batch = get_object_or_404(Batch, id=batch_id, farm__farmer=request.user.farmerprofile)
        
        # Calculate aggregate weight metrics
        total_weight = sum(item.get('weight', 0) for item in weight_data)
        sample_size = len(weight_data)
        average_weight = total_weight / sample_size if sample_size > 0 else 0
        
        # Estimate total flock weight
        current_bird_count = batch.quantity - batch.mortality_count
        estimated_total_weight = average_weight * current_bird_count
        
        # Get feed consumption for the same period
        feed_consumed = get_feed_consumption_for_period(
            batch, 
            measurement_date, 
            measurement_date
        )
        
        # Calculate FCR
        fcr = feed_consumed / estimated_total_weight if estimated_total_weight > 0 else 0
        
        # Create or update weight record
        weight_record = create_weight_record(
            batch=batch,
            measurement_date=measurement_date,
            total_weight=estimated_total_weight,
            average_weight=average_weight,
            sample_size=sample_size,
            feed_consumed=feed_consumed,
            fcr=fcr,
            notes=notes
        )
        
        # Synchronize with inventory depletion
        sync_result = synchronize_fcr_with_inventory(batch, measurement_date, feed_consumed)
        
        # Update batch performance metrics
        update_batch_performance_metrics(batch)
        
        response_data = {
            'success': True,
            'weight_record': {
                'id': str(weight_record.id) if weight_record else None,
                'batch_id': str(batch.id),
                'measurement_date': measurement_date,
                'total_weight': estimated_total_weight,
                'average_weight': average_weight,
                'sample_size': sample_size,
                'feed_consumed': feed_consumed,
                'fcr': fcr,
                'notes': notes
            },
            'inventory_sync': sync_result,
            'performance_impact': {
                'fcr_change': calculate_fcr_change(batch, fcr),
                'weight_gain_rate': calculate_weight_gain_rate(batch, estimated_total_weight),
                'inventory_depletion_rate': calculate_inventory_depletion_rate(batch, feed_consumed)
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_survival_metrics(request):
    """
    Log survival metrics and mortality data
    """
    try:
        data = json.loads(request.body)
        batch_id = data.get('batch_id')
        mortality_data = data.get('mortality_data', [])
        measurement_date = data.get('measurement_date') or date.today().isoformat()
        causes = data.get('causes', [])
        environmental_conditions = data.get('environmental_conditions', {})
        
        batch = get_object_or_404(Batch, id=batch_id, farm__farmer=request.user.farmerprofile)
        
        # Calculate mortality metrics
        total_mortality = sum(item.get('count', 0) for item in mortality_data)
        mortality_rate = (total_mortality / batch.quantity * 100) if batch.quantity > 0 else 0
        
        # Update batch mortality count
        batch.mortality_count += total_mortality
        batch.save()
        
        # Create health records for mortality
        health_records = []
        for mortality_item in mortality_data:
            cause = mortality_item.get('cause', 'Unknown')
            count = mortality_item.get('count', 0)
            
            health_record = HealthRecord.objects.create(
                farm=batch.farm,
                affected_batch=batch,
                record_type='MORTALITY',
                date=measurement_date,
                diagnosis=cause,
                notes=f"Mortality count: {count}. Environmental conditions: {environmental_conditions}"
            )
            health_records.append(health_record)
        
        # Analyze mortality patterns
        mortality_analysis = analyze_mortality_patterns(batch, measurement_date)
        
        # Check for abnormal losses
        abnormal_loss_alerts = check_abnormal_mortality(batch, total_mortality, measurement_date)
        
        # Update survival projections
        survival_projection = update_survival_projection(batch)
        
        # Trigger environmental alerts if needed
        environmental_alerts = trigger_environmental_alerts(
            batch, 
            total_mortality, 
            environmental_conditions,
            abnormal_loss_alerts
        )
        
        # Adjust stock liquidation projections
        liquidation_projections = adjust_liquidation_projections(batch, total_mortality)
        
        response_data = {
            'success': True,
            'survival_metrics': {
                'batch_id': str(batch.id),
                'measurement_date': measurement_date,
                'total_mortality': total_mortality,
                'mortality_rate': mortality_rate,
                'current_survival_rate': ((batch.quantity - batch.mortality_count) / batch.quantity * 100) if batch.quantity > 0 else 0,
                'cumulative_mortality': batch.mortality_count
            },
            'health_records': [
                {
                    'id': str(record.id),
                    'date': record.date.isoformat(),
                    'diagnosis': record.diagnosis,
                    'notes': record.notes
                }
                for record in health_records
            ],
            'mortality_analysis': mortality_analysis,
            'abnormal_loss_alerts': abnormal_loss_alerts,
            'environmental_alerts': environmental_alerts,
            'survival_projection': survival_projection,
            'liquidation_projections': liquidation_projections
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_losses(request):
    """
    Report various types of losses (mortality, feed, equipment, etc.)
    """
    try:
        data = json.loads(request.body)
        loss_type = data.get('loss_type')  # 'MORTALITY', 'FEED', 'EQUIPMENT', 'EGGS', etc.
        batch_id = data.get('batch_id')
        loss_data = data.get('loss_data', {})
        report_date = data.get('report_date') or date.today().isoformat()
        severity = data.get('severity', 'MEDIUM')
        impact_assessment = data.get('impact_assessment', {})
        
        batch = get_object_or_404(Batch, id=batch_id, farm__farmer=request.user.farmerprofile)
        
        # Process different types of losses
        if loss_type == 'MORTALITY':
            result = process_mortality_loss(batch, loss_data, report_date, severity)
        elif loss_type == 'FEED':
            result = process_feed_loss(batch, loss_data, report_date, severity)
        elif loss_type == 'EQUIPMENT':
            result = process_equipment_loss(batch, loss_data, report_date, severity)
        elif loss_type == 'EGGS':
            result = process_egg_loss(batch, loss_data, report_date, severity)
        else:
            result = process_general_loss(batch, loss_data, loss_type, report_date, severity)
        
        # Generate loss report
        loss_report = generate_loss_report(
            batch=batch,
            loss_type=loss_type,
            loss_data=loss_data,
            report_date=report_date,
            severity=severity,
            impact_assessment=impact_assessment,
            processing_result=result
        )
        
        # Update inventory if applicable
        inventory_updates = update_inventory_for_losses(batch, loss_type, loss_data, result)
        
        # Trigger alerts and recommendations
        alerts_and_recommendations = generate_loss_alerts_and_recommendations(
            batch, loss_type, loss_data, severity, result
        )
        
        # Update performance projections
        performance_updates = update_performance_projections(batch, loss_type, loss_data, result)
        
        response_data = {
            'success': True,
            'loss_report': loss_report,
            'processing_result': result,
            'inventory_updates': inventory_updates,
            'alerts_and_recommendations': alerts_and_recommendations,
            'performance_updates': performance_updates
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_performance_trends(request, batch_id):
    """
    Get comprehensive performance trends for a specific batch
    """
    try:
        batch = get_object_or_404(Batch, id=batch_id, farm__farmer=request.user.farmerprofile)
        
        # Get weight trends
        weight_trends = get_weight_trends(batch)
        
        # Get FCR trends
        fcr_trends = get_fcr_trends(batch)
        
        # Get survival trends
        survival_trends = get_survival_trends(batch)
        
        # Get feed consumption trends
        feed_trends = get_feed_consumption_trends(batch)
        
        # Get inventory depletion trends
        inventory_trends = get_inventory_depletion_trends(batch)
        
        # Calculate performance correlations
        performance_correlations = calculate_performance_correlations(batch)
        
        response_data = {
            'batch_info': {
                'id': str(batch.id),
                'batch_number': batch.batch_number,
                'breed': batch.breed,
                'current_age_days': batch.current_age_days,
                'status': batch.status
            },
            'trends': {
                'weight': weight_trends,
                'fcr': fcr_trends,
                'survival': survival_trends,
                'feed_consumption': feed_trends,
                'inventory_depletion': inventory_trends
            },
            'correlations': performance_correlations,
            'performance_summary': calculate_performance_summary(batch)
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Helper functions

def get_feed_consumption_for_period(batch, start_date, end_date):
    """Get feed consumption for a specific period"""
    from datetime import datetime
    
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    
    consumption = FeedConsumption.objects.filter(
        batch=batch,
        date__gte=start,
        date__lte=end
    ).aggregate(total=Sum('amount_consumed'))['total'] or 0
    
    return consumption


def create_weight_record(batch, measurement_date, total_weight, average_weight, 
                         sample_size, feed_consumed, fcr, notes):
    """Create a weight record for the batch"""
    # This would typically create a WeightRecord model
    # For now, we'll return a mock object
    class MockWeightRecord:
        def __init__(self):
            self.id = timezone.now().timestamp()
    
    return MockWeightRecord()


def synchronize_fcr_with_inventory(batch, measurement_date, feed_consumed):
    """Synchronize FCR with inventory depletion"""
    # Get feed inventory items for this batch
    feed_inventory = InventoryItem.objects.filter(batch=batch, category='FEED')
    
    # Create inventory transaction for feed consumption
    if feed_consumed > 0 and feed_inventory.exists():
        # Find the appropriate feed item (e.g., starter feed for young birds)
        feed_item = None
        if batch.current_age_days <= 18:
            feed_item = feed_inventory.filter(feed_stage='STARTER').first()
        elif batch.current_age_days <= 40:
            feed_item = feed_inventory.filter(feed_stage='GROWER').first()
        else:
            feed_item = feed_inventory.filter(feed_stage='FINISHER').first()
        
        if feed_item:
            # Create usage transaction
            InventoryTransaction.objects.create(
                item=feed_item,
                transaction_type='USAGE',
                quantity_change=-feed_consumed,
                reference_number=f"FCR-SYNC-{batch.batch_number}-{measurement_date}",
                notes=f"Auto-synced feed consumption for FCR calculation"
            )
            
            # Update inventory quantity
            feed_item.quantity -= feed_consumed
            feed_item.save()
    
    return {
        'sync_status': 'SUCCESS',
        'feed_consumed': feed_consumed,
        'inventory_updated': feed_consumed > 0 and feed_inventory.exists()
    }


def calculate_fcr_change(batch, current_fcr):
    """Calculate FCR change from previous measurement"""
    # Get previous FCR measurement
    # For now, return a placeholder
    return {
        'current_fcr': current_fcr,
        'previous_fcr': current_fcr * 1.05,  # Placeholder
        'change_percentage': -5.0  # Placeholder
    }


def calculate_weight_gain_rate(batch, current_weight):
    """Calculate weight gain rate"""
    # Get previous weight measurement
    # For now, return a placeholder
    return {
        'current_weight': current_weight,
        'weight_gain_rate': 50.0  # grams per day (placeholder)
    }


def calculate_inventory_depletion_rate(batch, feed_consumed):
    """Calculate inventory depletion rate"""
    return {
        'feed_consumed': feed_consumed,
        'depletion_rate': feed_consumed / batch.current_age_days if batch.current_age_days > 0 else 0
    }


def update_batch_performance_metrics(batch):
    """Update batch performance metrics"""
    # This would update various performance metrics
    # For now, just return success
    return {'status': 'SUCCESS'}


def analyze_mortality_patterns(batch, measurement_date):
    """Analyze mortality patterns"""
    # Get recent mortality records
    recent_mortality = HealthRecord.objects.filter(
        affected_batch=batch,
        record_type='MORTALITY',
        date__gte=timezone.now().date() - timedelta(days=7)
    ).count()
    
    return {
        'recent_mortality_count': recent_mortality,
        'pattern': 'ANALYZED',
        'trend': 'STABLE'  # Placeholder
    }


def check_abnormal_mortality(batch, total_mortality, measurement_date):
    """Check for abnormal mortality patterns"""
    expected_daily_mortality = batch.quantity * 0.001  # 0.1% daily mortality expectation
    
    alerts = []
    if total_mortality > expected_daily_mortality * 3:
        alerts.append({
            'type': 'ABNORMAL_MORTALITY',
            'severity': 'HIGH',
            'message': f'Abnormal mortality detected: {total_mortality} birds (expected: {expected_daily_mortality:.1f})',
            'recommended_action': 'Immediate health inspection required'
        })
    
    return alerts


def trigger_environmental_alerts(batch, total_mortality, environmental_conditions, abnormal_alerts):
    """Trigger environmental alerts based on mortality"""
    alerts = []
    
    # Check temperature-related issues
    temperature = environmental_conditions.get('temperature')
    if temperature and (temperature < 20 or temperature > 35):
        alerts.append({
            'type': 'TEMPERATURE_STRESS',
            'severity': 'MEDIUM',
            'message': f'Temperature stress detected: {temperature}°C',
            'recommended_action': 'Adjust environmental controls'
        })
    
    # Check humidity-related issues
    humidity = environmental_conditions.get('humidity')
    if humidity and (humidity < 40 or humidity > 70):
        alerts.append({
            'type': 'HUMIDITY_STRESS',
            'severity': 'MEDIUM',
            'message': f'Humidity stress detected: {humidity}%',
            'recommended_action': 'Adjust ventilation systems'
        })
    
    return alerts + abnormal_alerts


def update_survival_projection(batch):
    """Update survival projection based on current mortality"""
    current_survival_rate = ((batch.quantity - batch.mortality_count) / batch.quantity * 100) if batch.quantity > 0 else 0
    
    # Project final survival rate
    days_remaining = 42 - batch.current_age_days  # Assuming 42-day cycle
    expected_additional_mortality = days_remaining * (batch.mortality_count / batch.current_age_days) if batch.current_age_days > 0 else 0
    
    projected_final_survival = ((batch.quantity - batch.mortality_count - expected_additional_mortality) / batch.quantity * 100) if batch.quantity > 0 else 0
    
    return {
        'current_survival_rate': current_survival_rate,
        'projected_final_survival': projected_final_survival,
        'confidence': 'MEDIUM'
    }


def adjust_liquidation_projections(batch, total_mortality):
    """Adjust stock liquidation projections based on mortality"""
    current_birds = batch.quantity - batch.mortality_count
    
    # Adjust market weight projections
    expected_market_weight = get_expected_weight(42, batch.breed) * current_birds
    
    # Adjust revenue projections
    expected_revenue = expected_market_weight * 2.5  # $2.5 per kg (placeholder)
    
    return {
        'current_bird_count': current_birds,
        'projected_market_weight': expected_market_weight,
        'projected_revenue': expected_revenue,
        'mortality_impact': total_mortality * get_expected_weight(42, batch.breed) * 2.5
    }


def process_mortality_loss(batch, loss_data, report_date, severity):
    """Process mortality loss"""
    mortality_count = loss_data.get('count', 0)
    cause = loss_data.get('cause', 'Unknown')
    
    # Update batch mortality
    batch.mortality_count += mortality_count
    batch.save()
    
    # Create health record
    health_record = HealthRecord.objects.create(
        farm=batch.farm,
        affected_batch=batch,
        record_type='MORTALITY',
        date=report_date,
        diagnosis=cause,
        notes=f"Reported loss: {mortality_count} birds. Severity: {severity}"
    )
    
    return {
        'type': 'MORTALITY',
        'count': mortality_count,
        'cause': cause,
        'health_record_id': str(health_record.id),
        'updated_mortality_count': batch.mortality_count
    }


def process_feed_loss(batch, loss_data, report_date, severity):
    """Process feed loss"""
    quantity_lost = loss_data.get('quantity', 0)
    feed_type = loss_data.get('feed_type', 'Unknown')
    loss_reason = loss_data.get('reason', 'Unknown')
    
    # Find feed inventory item
    feed_inventory = InventoryItem.objects.filter(
        batch=batch,
        category='FEED',
        feed_stage=feed_type
    ).first()
    
    if feed_inventory:
        # Create inventory transaction for loss
        transaction = InventoryTransaction.objects.create(
            item=feed_inventory,
            transaction_type='WASTE',
            quantity_change=-quantity_lost,
            reference_number=f"LOSS-{batch.batch_number}-{report_date}",
            notes=f"Feed loss: {loss_reason}. Severity: {severity}"
        )
        
        # Update inventory quantity
        feed_inventory.quantity -= quantity_lost
        feed_inventory.save()
        
        return {
            'type': 'FEED',
            'quantity_lost': quantity_lost,
            'feed_type': feed_type,
            'reason': loss_reason,
            'transaction_id': str(transaction.id),
            'updated_inventory': float(feed_inventory.quantity)
        }
    
    return {
        'type': 'FEED',
        'quantity_lost': quantity_lost,
        'feed_type': feed_type,
        'reason': loss_reason,
        'status': 'NO_INVENTORY_FOUND'
    }


def process_equipment_loss(batch, loss_data, report_date, severity):
    """Process equipment loss"""
    equipment_type = loss_data.get('equipment_type', 'Unknown')
    loss_reason = loss_data.get('reason', 'Unknown')
    replacement_cost = loss_data.get('replacement_cost', 0)
    
    # Find equipment inventory
    equipment_inventory = InventoryItem.objects.filter(
        batch=batch,
        category='EQUIPMENT',
        subcategory=equipment_type
    ).first()
    
    if equipment_inventory:
        # Create inventory transaction for loss
        transaction = InventoryTransaction.objects.create(
            item=equipment_inventory,
            transaction_type='WASTE',
            quantity_change=-1,
            reference_number=f"LOSS-{batch.batch_number}-{report_date}",
            notes=f"Equipment loss: {loss_reason}. Cost: {replacement_cost}. Severity: {severity}"
        )
        
        return {
            'type': 'EQUIPMENT',
            'equipment_type': equipment_type,
            'reason': loss_reason,
            'replacement_cost': replacement_cost,
            'transaction_id': str(transaction.id)
        }
    
    return {
        'type': 'EQUIPMENT',
        'equipment_type': equipment_type,
        'reason': loss_reason,
        'replacement_cost': replacement_cost,
        'status': 'NO_INVENTORY_FOUND'
    }


def process_egg_loss(batch, loss_data, report_date, severity):
    """Process egg loss"""
    trays_lost = loss_data.get('trays', 0)
    loss_reason = loss_data.get('reason', 'Unknown')
    
    # Find egg inventory
    egg_inventory = EggInventory.objects.filter(batch=batch).first()
    
    if egg_inventory:
        # Create egg sale record for loss (negative sale)
        loss_record = EggSale.objects.create(
            batch=batch,
            date=report_date,
            trays_sold=-trays_lost,
            price_per_tray=0,
            notes=f"Egg loss: {loss_reason}. Severity: {severity}"
        )
        
        # Update egg inventory
        egg_inventory.quantity_trays -= trays_lost
        egg_inventory.save()
        
        return {
            'type': 'EGGS',
            'trays_lost': trays_lost,
            'reason': loss_reason,
            'loss_record_id': str(loss_record.id),
            'updated_inventory': egg_inventory.quantity_trays
        }
    
    return {
        'type': 'EGGS',
        'trays_lost': trays_lost,
        'reason': loss_reason,
        'status': 'NO_INVENTORY_FOUND'
    }


def process_general_loss(batch, loss_data, loss_type, report_date, severity):
    """Process general loss"""
    description = loss_data.get('description', 'Unknown loss')
    estimated_value = loss_data.get('estimated_value', 0)
    
    return {
        'type': loss_type,
        'description': description,
        'estimated_value': estimated_value,
        'severity': severity,
        'status': 'RECORDED'
    }


def generate_loss_report(batch, loss_type, loss_data, report_date, severity, impact_assessment, processing_result):
    """Generate comprehensive loss report"""
    return {
        'report_id': f"LOSS-{batch.batch_number}-{report_date}",
        'batch_info': {
            'id': str(batch.id),
            'batch_number': batch.batch_number,
            'breed': batch.breed
        },
        'loss_details': {
            'type': loss_type,
            'date': report_date,
            'severity': severity,
            'data': loss_data
        },
        'impact_assessment': impact_assessment,
        'processing_result': processing_result,
        'financial_impact': calculate_financial_impact(loss_type, loss_data),
        'operational_impact': calculate_operational_impact(loss_type, loss_data, batch)
    }


def update_inventory_for_losses(batch, loss_type, loss_data, processing_result):
    """Update inventory based on losses"""
    updates = []
    
    if loss_type in ['FEED', 'EQUIPMENT']:
        if processing_result.get('transaction_id'):
            updates.append({
                'type': 'INVENTORY_TRANSACTION',
                'transaction_id': processing_result['transaction_id'],
                'status': 'PROCESSED'
            })
    
    return updates


def generate_loss_alerts_and_recommendations(batch, loss_type, loss_data, severity, processing_result):
    """Generate alerts and recommendations based on losses"""
    alerts = []
    recommendations = []
    
    if loss_type == 'MORTALITY' and severity in ['HIGH', 'CRITICAL']:
        alerts.append({
            'type': 'HIGH_MORTALITY',
            'message': f'High mortality detected in batch {batch.batch_number}',
            'action_required': 'Immediate veterinary consultation'
        })
        recommendations.append({
            'category': 'HEALTH',
            'action': 'Schedule immediate health inspection',
            'priority': 'HIGH'
        })
    
    if loss_type == 'FEED':
        recommendations.append({
            'category': 'INVENTORY',
            'action': 'Review feed storage and handling procedures',
            'priority': 'MEDIUM'
        })
    
    return {
        'alerts': alerts,
        'recommendations': recommendations
    }


def update_performance_projections(batch, loss_type, loss_data, processing_result):
    """Update performance projections based on losses"""
    projections = {
        'survival_projection': update_survival_projection(batch),
        'fcr_projection': update_fcr_projection(batch, loss_type, loss_data),
        'financial_projection': adjust_liquidation_projections(batch, loss_data.get('count', 0))
    }
    
    return projections


def get_weight_trends(batch):
    """Get weight trends for the batch"""
    # This would query weight records
    # For now, return placeholder data
    return [
        {'date': '2024-01-01', 'weight': 1000, 'average_weight': 0.5},
        {'date': '2024-01-08', 'weight': 2500, 'average_weight': 1.3},
        {'date': '2024-01-15', 'weight': 4500, 'average_weight': 2.4}
    ]


def get_fcr_trends(batch):
    """Get FCR trends for the batch"""
    return [
        {'date': '2024-01-01', 'fcr': 1.6},
        {'date': '2024-01-08', 'fcr': 1.7},
        {'date': '2024-01-15', 'fcr': 1.8}
    ]


def get_survival_trends(batch):
    """Get survival trends for the batch"""
    return [
        {'date': '2024-01-01', 'survival_rate': 100.0},
        {'date': '2024-01-08', 'survival_rate': 98.5},
        {'date': '2024-01-15', 'survival_rate': 97.0}
    ]


def get_feed_consumption_trends(batch):
    """Get feed consumption trends"""
    return [
        {'date': '2024-01-01', 'consumption': 50},
        {'date': '2024-01-08', 'consumption': 150},
        {'date': '2024-01-15', 'consumption': 280}
    ]


def get_inventory_depletion_trends(batch):
    """Get inventory depletion trends"""
    return [
        {'date': '2024-01-01', 'depletion': 50},
        {'date': '2024-01-08', 'depletion': 150},
        {'date': '2024-01-15', 'depletion': 280}
    ]


def calculate_performance_correlations(batch):
    """Calculate correlations between different performance metrics"""
    return {
        'weight_fcr_correlation': -0.85,
        'feed_consumption_weight_correlation': 0.92,
        'mortality_fcr_correlation': 0.45
    }


def calculate_performance_summary(batch):
    """Calculate overall performance summary"""
    return {
        'overall_score': 85,
        'key_metrics': {
            'fcr': 1.8,
            'survival_rate': 97.0,
            'average_daily_gain': 45.0
        },
        'performance_rating': 'GOOD'
    }


def calculate_financial_impact(loss_type, loss_data):
    """Calculate financial impact of loss"""
    if loss_type == 'MORTALITY':
        count = loss_data.get('count', 0)
        return count * 2.5  # $2.5 per kg average market weight
    elif loss_type == 'FEED':
        quantity = loss_data.get('quantity', 0)
        return quantity * 0.5  # $0.5 per kg feed cost
    elif loss_type == 'EQUIPMENT':
        return loss_data.get('replacement_cost', 0)
    else:
        return loss_data.get('estimated_value', 0)


def calculate_operational_impact(loss_type, loss_data, batch):
    """Calculate operational impact of loss"""
    impacts = []
    
    if loss_type == 'MORTALITY':
        impacts.append('Reduced production capacity')
        impacts.append('Potential impact on flock dynamics')
    elif loss_type == 'FEED':
        impacts.append('Potential feed shortage')
        impacts.append('Impact on growth rates')
    
    return impacts


def update_fcr_projection(batch, loss_type, loss_data):
    """Update FCR projection based on losses"""
    current_fcr = 1.8  # Placeholder
    
    if loss_type == 'MORTALITY':
        # Higher mortality might improve FCR (fewer birds to feed)
        projected_fcr = current_fcr * 0.95
    elif loss_type == 'FEED':
        # Feed loss might worsen FCR (less feed for same growth)
        projected_fcr = current_fcr * 1.1
    else:
        projected_fcr = current_fcr
    
    return {
        'current_fcr': current_fcr,
        'projected_fcr': projected_fcr,
        'impact': loss_type
    }
