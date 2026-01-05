from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Q, F, FloatField, Count, Avg, StdDev, Variance
from django.utils import timezone
from datetime import date, timedelta, datetime
import json

from apps.consolidated.models import (
    Batch, Farm, InventoryItem, InventoryTransaction, 
    FeedConsumption, HealthRecord, EggInventory, EggSale
)
from apps.consolidated.serializers import (
    BatchSerializer, InventoryItemSerializer, FeedConsumptionSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def performance_hub_dashboard(request):
    """
    Main Performance Hub Dashboard
    Provides comprehensive flock performance metrics with FCR synchronization
    """
    try:
        farmer = request.user.farmerprofile
        
        # Get all active batches for the farmer
        active_batches = Batch.objects.filter(
            farm__farmer=farmer,
            status='ACTIVE'
        ).order_by('-created_at')
        
        # Calculate comprehensive performance metrics
        performance_data = []
        
        for batch in active_batches:
            batch_metrics = calculate_batch_performance_metrics(batch)
            performance_data.append(batch_metrics)
        
        # Calculate aggregate metrics across all batches
        aggregate_metrics = calculate_aggregate_performance_metrics(active_batches)
        
        # FCR Analysis with inventory synchronization
        fcr_analysis = calculate_fcr_analysis(active_batches)
        
        # Survival and loss analysis
        survival_analysis = calculate_survival_analysis(active_batches)
        
        # Environmental alerts based on performance
        environmental_alerts = generate_environmental_alerts(active_batches)
        
        response_data = {
            'performance_summary': {
                'total_active_batches': active_batches.count(),
                'total_birds': sum(batch['current_bird_count'] for batch in performance_data),
                'average_fcr': aggregate_metrics['average_fcr'],
                'overall_survival_rate': aggregate_metrics['overall_survival_rate'],
                'total_feed_consumed': aggregate_metrics['total_feed_consumed'],
                'total_weight_gained': aggregate_metrics['total_weight_gained'],
                'performance_score': aggregate_metrics['performance_score']
            },
            'batch_performance': performance_data,
            'fcr_analysis': fcr_analysis,
            'survival_analysis': survival_analysis,
            'environmental_alerts': environmental_alerts,
            'inventory_sync_status': check_inventory_sync_status(active_batches),
            'last_updated': timezone.now().isoformat()
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def calculate_batch_performance_metrics(batch):
    """
    Calculate comprehensive performance metrics for a specific batch
    """
    # Get current bird count
    current_bird_count = batch.quantity - batch.mortality_count
    
    # Get feed consumption data
    feed_consumption = FeedConsumption.objects.filter(batch=batch)
    total_feed_consumed = feed_consumption.aggregate(
        total=Sum('amount_consumed')
    )['total'] or 0
    
    # Get weight data (this would typically come from weighing records)
    # For now, we'll estimate based on age and breed
    estimated_weight = estimate_batch_weight(batch)
    
    # Calculate FCR
    fcr = calculate_fcr(total_feed_consumed, estimated_weight, current_bird_count)
    
    # Calculate growth rate
    growth_rate = calculate_growth_rate(batch, estimated_weight)
    
    # Get health records
    health_records = HealthRecord.objects.filter(affected_batch=batch)
    health_issues = health_records.count()
    
    # Calculate survival rate
    survival_rate = (current_bird_count / batch.quantity * 100) if batch.quantity > 0 else 0
    
    # Get egg production if applicable
    egg_production = calculate_egg_production(batch)
    
    return {
        'batch_id': str(batch.id),
        'batch_number': batch.batch_number,
        'breed': batch.breed,
        'current_age_days': batch.current_age_days,
        'initial_quantity': batch.quantity,
        'current_bird_count': current_bird_count,
        'mortality_count': batch.mortality_count,
        'survival_rate': survival_rate,
        'estimated_weight': estimated_weight,
        'total_feed_consumed': total_feed_consumed,
        'fcr': fcr,
        'growth_rate': growth_rate,
        'health_issues': health_issues,
        'egg_production': egg_production,
        'performance_score': calculate_performance_score(fcr, survival_rate, growth_rate),
        'status': batch.status
    }


def calculate_aggregate_performance_metrics(batches):
    """
    Calculate aggregate performance metrics across all batches
    """
    if not batches.exists():
        return {
            'average_fcr': 0,
            'overall_survival_rate': 0,
            'total_feed_consumed': 0,
            'total_weight_gained': 0,
            'performance_score': 0
        }
    
    total_birds = batches.aggregate(total=Sum('quantity'))['total'] or 0
    total_mortality = batches.aggregate(total=Sum('mortality_count'))['total'] or 0
    total_feed_consumed = FeedConsumption.objects.filter(
        batch__in=batches
    ).aggregate(total=Sum('amount_consumed'))['total'] or 0
    
    # Calculate total weight (estimated)
    total_weight = sum(estimate_batch_weight(batch) for batch in batches)
    
    # Calculate overall FCR
    overall_fcr = calculate_fcr(total_feed_consumed, total_weight, total_birds - total_mortality)
    
    # Calculate overall survival rate
    overall_survival_rate = ((total_birds - total_mortality) / total_birds * 100) if total_birds > 0 else 0
    
    # Calculate average performance score
    performance_scores = []
    for batch in batches:
        fcr = calculate_fcr(
            FeedConsumption.objects.filter(batch=batch).aggregate(total=Sum('amount_consumed'))['total'] or 0,
            estimate_batch_weight(batch),
            batch.quantity - batch.mortality_count
        )
        survival_rate = ((batch.quantity - batch.mortality_count) / batch.quantity * 100) if batch.quantity > 0 else 0
        growth_rate = calculate_growth_rate(batch, estimate_batch_weight(batch))
        performance_scores.append(calculate_performance_score(fcr, survival_rate, growth_rate))
    
    average_performance_score = sum(performance_scores) / len(performance_scores) if performance_scores else 0
    
    return {
        'average_fcr': overall_fcr,
        'overall_survival_rate': overall_survival_rate,
        'total_feed_consumed': total_feed_consumed,
        'total_weight_gained': total_weight,
        'performance_score': average_performance_score
    }


def calculate_fcr_analysis(batches):
    """
    Comprehensive FCR analysis with inventory synchronization
    """
    fcr_data = []
    
    for batch in batches:
        # Get daily feed consumption
        daily_consumption = FeedConsumption.objects.filter(batch=batch).order_by('date')
        
        # Calculate daily FCR trend
        fcr_trend = []
        cumulative_feed = 0
        cumulative_weight = 0
        
        for consumption in daily_consumption:
            cumulative_feed += consumption.amount_consumed
            # Estimate weight gain for this period
            daily_weight_gain = estimate_daily_weight_gain(batch, consumption.date)
            cumulative_weight += daily_weight_gain
            
            if cumulative_weight > 0:
                daily_fcr = cumulative_feed / cumulative_weight
                fcr_trend.append({
                    'date': consumption.date.isoformat(),
                    'cumulative_feed': cumulative_feed,
                    'cumulative_weight': cumulative_weight,
                    'fcr': daily_fcr
                })
        
        # Get inventory synchronization status
        inventory_sync = get_inventory_fcr_sync(batch)
        
        fcr_data.append({
            'batch_id': str(batch.id),
            'batch_number': batch.batch_number,
            'current_fcr': calculate_fcr(
                FeedConsumption.objects.filter(batch=batch).aggregate(total=Sum('amount_consumed'))['total'] or 0,
                estimate_batch_weight(batch),
                batch.quantity - batch.mortality_count
            ),
            'fcr_trend': fcr_trend,
            'target_fcr': get_target_fcr(batch.breed),
            'fcr_performance': get_fcr_performance_rating(
                calculate_fcr(
                    FeedConsumption.objects.filter(batch=batch).aggregate(total=Sum('amount_consumed'))['total'] or 0,
                    estimate_batch_weight(batch),
                    batch.quantity - batch.mortality_count
                ),
                get_target_fcr(batch.breed)
            ),
            'inventory_sync': inventory_sync
        })
    
    return {
        'batch_fcr_data': fcr_data,
        'overall_fcr_trend': calculate_overall_fcr_trend(batches),
        'fcr_benchmarks': get_fcr_benchmarks(),
        'inventory_depletion_sync': check_inventory_depletion_sync(batches)
    }


def calculate_survival_analysis(batches):
    """
    Comprehensive survival and loss analysis
    """
    survival_data = []
    
    for batch in batches:
        # Get mortality records
        mortality_records = HealthRecord.objects.filter(
            affected_batch=batch,
            record_type='MORTALITY'
        ).order_by('date')
        
        # Calculate daily survival trend
        survival_trend = []
        cumulative_mortality = 0
        
        for record in mortality_records:
            cumulative_mortality += get_mortality_count(record)
            current_survival_rate = ((batch.quantity - cumulative_mortality) / batch.quantity * 100) if batch.quantity > 0 else 0
            
            survival_trend.append({
                'date': record.date.isoformat(),
                'cumulative_mortality': cumulative_mortality,
                'survival_rate': current_survival_rate,
                'daily_mortality': get_mortality_count(record),
                'cause': record.diagnosis or 'Unknown'
            })
        
        # Analyze loss patterns
        loss_analysis = analyze_loss_patterns(batch)
        
        survival_data.append({
            'batch_id': str(batch.id),
            'batch_number': batch.batch_number,
            'initial_quantity': batch.quantity,
            'current_quantity': batch.quantity - batch.mortality_count,
            'total_mortality': batch.mortality_count,
            'survival_rate': ((batch.quantity - batch.mortality_count) / batch.quantity * 100) if batch.quantity > 0 else 0,
            'survival_trend': survival_trend,
            'loss_analysis': loss_analysis,
            'mortality_causes': get_mortality_cause_analysis(batch),
            'survival_projection': calculate_survival_projection(batch)
        })
    
    return {
        'batch_survival_data': survival_data,
        'overall_survival_trend': calculate_overall_survival_trend(batches),
        'mortality_causes_summary': get_mortality_causes_summary(batches),
        'abnormal_losses': detect_abnormal_losses(batches),
        'survival_benchmarks': get_survival_benchmarks()
    }


def generate_environmental_alerts(batches):
    """
    Generate environmental alerts based on performance data
    """
    alerts = []
    
    for batch in batches:
        # Check for abnormal mortality
        current_mortality_rate = (batch.mortality_count / batch.quantity * 100) if batch.quantity > 0 else 0
        expected_mortality_rate = get_expected_mortality_rate(batch.current_age_days, batch.breed)
        
        if current_mortality_rate > expected_mortality_rate * 1.5:
            alerts.append({
                'type': 'ABNORMAL_MORTALITY',
                'severity': 'HIGH',
                'batch_id': str(batch.id),
                'batch_number': batch.batch_number,
                'message': f'Abnormal mortality detected: {current_mortality_rate:.1f}% (expected: {expected_mortality_rate:.1f}%)',
                'recommended_action': 'Immediate health inspection and environmental review',
                'affected_systems': ['health', 'environment', 'nutrition']
            })
        
        # Check for poor FCR
        current_fcr = calculate_fcr(
            FeedConsumption.objects.filter(batch=batch).aggregate(total=Sum('amount_consumed'))['total'] or 0,
            estimate_batch_weight(batch),
            batch.quantity - batch.mortality_count
        )
        target_fcr = get_target_fcr(batch.breed)
        
        if current_fcr > target_fcr * 1.2:
            alerts.append({
                'type': 'POOR_FCR',
                'severity': 'MEDIUM',
                'batch_id': str(batch.id),
                'batch_number': batch.batch_number,
                'message': f'Poor FCR detected: {current_fcr:.2f} (target: {target_fcr:.2f})',
                'recommended_action': 'Review feed quality and environmental conditions',
                'affected_systems': ['nutrition', 'environment']
            })
        
        # Check for growth issues
        expected_weight = get_expected_weight(batch.current_age_days, batch.breed)
        actual_weight = estimate_batch_weight(batch)
        
        if actual_weight < expected_weight * 0.8:
            alerts.append({
                'type': 'GROWTH_ISSUES',
                'severity': 'MEDIUM',
                'batch_id': str(batch.id),
                'batch_number': batch.batch_number,
                'message': f'Growth issues detected: {actual_weight:.1f}kg (expected: {expected_weight:.1f}kg)',
                'recommended_action': 'Review nutrition and health status',
                'affected_systems': ['nutrition', 'health']
            })
    
    return alerts


def check_inventory_sync_status(batches):
    """
    Check inventory synchronization status with performance data
    """
    sync_status = []
    
    for batch in batches:
        # Get feed inventory items for this batch
        feed_inventory = InventoryItem.objects.filter(batch=batch, category='FEED')
        
        # Calculate expected feed depletion based on consumption
        total_consumed = FeedConsumption.objects.filter(batch=batch).aggregate(
            total=Sum('amount_consumed')
        )['total'] or 0
        
        # Calculate actual inventory depletion
        inventory_transactions = InventoryTransaction.objects.filter(
            item__in=feed_inventory,
            transaction_type='USAGE'
        ).aggregate(total=Sum('quantity_change'))['total'] or 0
        
        sync_percentage = (inventory_transactions / total_consumed * 100) if total_consumed > 0 else 100
        
        sync_status.append({
            'batch_id': str(batch.id),
            'batch_number': batch.batch_number,
            'sync_percentage': sync_percentage,
            'sync_status': 'GOOD' if sync_percentage >= 95 else 'POOR' if sync_percentage >= 80 else 'CRITICAL',
            'total_consumed': total_consumed,
            'inventory_depletion': inventory_transactions,
            'discrepancy': total_consumed - inventory_transactions
        })
    
    return sync_status


# Helper functions for calculations

def estimate_batch_weight(batch):
    """Estimate total batch weight based on age and breed"""
    # This would typically use actual weighing records
    # For now, we'll use breed-specific growth curves
    weight_per_bird = get_expected_weight(batch.current_age_days, batch.breed)
    current_birds = batch.quantity - batch.mortality_count
    return weight_per_bird * current_birds


def get_expected_weight(age_days, breed):
    """Get expected weight per bird based on age and breed"""
    # Simplified growth curves - in practice, this would use breed-specific data
    growth_curves = {
        'BROILER': {
            1: 0.04, 7: 0.15, 14: 0.40, 21: 0.85, 28: 1.35, 35: 1.90, 42: 2.50
        },
        'LAYER': {
            1: 0.03, 7: 0.12, 14: 0.30, 21: 0.55, 28: 0.80, 35: 1.10, 42: 1.40
        }
    }
    
    curve = growth_curves.get(breed, growth_curves['BROILER'])
    
    # Find closest age point and interpolate
    ages = sorted(curve.keys())
    if age_days <= ages[0]:
        return curve[ages[0]]
    if age_days >= ages[-1]:
        return curve[ages[-1]]
    
    # Linear interpolation
    for i in range(len(ages) - 1):
        if ages[i] <= age_days <= ages[i + 1]:
            ratio = (age_days - ages[i]) / (ages[i + 1] - ages[i])
            return curve[ages[i]] + ratio * (curve[ages[i + 1]] - curve[ages[i]])
    
    return curve[ages[-1]]


def calculate_fcr(feed_consumed, total_weight, bird_count):
    """Calculate Feed Conversion Ratio"""
    if total_weight <= 0 or bird_count <= 0:
        return 0
    return feed_consumed / total_weight


def calculate_growth_rate(batch, current_weight):
    """Calculate daily growth rate"""
    if batch.current_age_days <= 0:
        return 0
    
    initial_weight = get_expected_weight(0, batch.breed) * batch.quantity
    weight_gain = current_weight - initial_weight
    return weight_gain / batch.current_age_days


def calculate_performance_score(fcr, survival_rate, growth_rate):
    """Calculate overall performance score"""
    # Normalize metrics and weight them
    fcr_score = max(0, 100 - (fcr - 1.5) * 20)  # Lower FCR is better
    survival_score = survival_rate  # Higher survival is better
    growth_score = min(100, growth_rate * 10)  # Higher growth is better
    
    # Weighted average
    return (fcr_score * 0.4 + survival_score * 0.4 + growth_score * 0.2)


def get_target_fcr(breed):
    """Get target FCR for breed"""
    targets = {
        'BROILER': 1.8,
        'LAYER': 2.2,
        'DUAL_PURPOSE': 2.0
    }
    return targets.get(breed, 2.0)


def get_fcr_performance_rating(current_fcr, target_fcr):
    """Get FCR performance rating"""
    if current_fcr <= target_fcr * 0.9:
        return 'EXCELLENT'
    elif current_fcr <= target_fcr:
        return 'GOOD'
    elif current_fcr <= target_fcr * 1.2:
        return 'FAIR'
    else:
        return 'POOR'


def get_inventory_fcr_sync(batch):
    """Get inventory FCR synchronization status"""
    # Get feed inventory transactions
    feed_inventory = InventoryItem.objects.filter(batch=batch, category='FEED')
    inventory_depletion = InventoryTransaction.objects.filter(
        item__in=feed_inventory,
        transaction_type='USAGE'
    ).aggregate(total=Sum('quantity_change'))['total'] or 0
    
    # Get actual feed consumption
    actual_consumption = FeedConsumption.objects.filter(batch=batch).aggregate(
        total=Sum('amount_consumed')
    )['total'] or 0
    
    sync_percentage = (inventory_depletion / actual_consumption * 100) if actual_consumption > 0 else 100
    
    return {
        'sync_percentage': sync_percentage,
        'status': 'GOOD' if sync_percentage >= 95 else 'POOR' if sync_percentage >= 80 else 'CRITICAL',
        'inventory_depletion': inventory_depletion,
        'actual_consumption': actual_consumption,
        'discrepancy': actual_consumption - inventory_depletion
    }


def get_mortality_count(health_record):
    """Extract mortality count from health record"""
    # This would typically be stored in the health record
    # For now, we'll use a reasonable default
    return 5


def analyze_loss_patterns(batch):
    """Analyze mortality patterns for a batch"""
    mortality_records = HealthRecord.objects.filter(
        affected_batch=batch,
        record_type='MORTALITY'
    ).order_by('date')
    
    if not mortality_records.exists():
        return {
            'pattern': 'STABLE',
            'peak_period': None,
            'trend': 'STABLE'
        }
    
    # Analyze mortality trends
    recent_mortality = mortality_records.filter(
        date__gte=timezone.now().date() - timedelta(days=7)
    ).count()
    
    earlier_mortality = mortality_records.filter(
        date__lt=timezone.now().date() - timedelta(days=7)
    ).count()
    
    if recent_mortality > earlier_mortality * 1.5:
        trend = 'INCREASING'
    elif recent_mortality < earlier_mortality * 0.5:
        trend = 'DECREASING'
    else:
        trend = 'STABLE'
    
    return {
        'pattern': 'ANALYZED',
        'recent_mortality': recent_mortality,
        'earlier_mortality': earlier_mortality,
        'trend': trend
    }


def get_mortality_cause_analysis(batch):
    """Analyze mortality causes for a batch"""
    health_records = HealthRecord.objects.filter(affected_batch=batch)
    
    causes = {}
    for record in health_records:
        cause = record.diagnosis or 'Unknown'
        causes[cause] = causes.get(cause, 0) + 1
    
    return causes


def calculate_survival_projection(batch):
    """Calculate survival projection for the batch"""
    current_survival_rate = ((batch.quantity - batch.mortality_count) / batch.quantity * 100) if batch.quantity > 0 else 0
    
    # Project based on current trend
    expected_final_survival = current_survival_rate * 0.95  # Assume slight decline
    
    return {
        'current_survival_rate': current_survival_rate,
        'projected_final_survival': expected_final_survival,
        'confidence': 'MEDIUM'
    }


def detect_abnormal_losses(batches):
    """Detect abnormal mortality patterns"""
    abnormal_losses = []
    
    for batch in batches:
        current_mortality_rate = (batch.mortality_count / batch.quantity * 100) if batch.quantity > 0 else 0
        expected_rate = get_expected_mortality_rate(batch.current_age_days, batch.breed)
        
        if current_mortality_rate > expected_rate * 2:
            abnormal_losses.append({
                'batch_id': str(batch.id),
                'batch_number': batch.batch_number,
                'severity': 'HIGH',
                'current_rate': current_mortality_rate,
                'expected_rate': expected_rate,
                'deviation': current_mortality_rate - expected_rate
            })
    
    return abnormal_losses


def get_expected_mortality_rate(age_days, breed):
    """Get expected mortality rate for age and breed"""
    # Simplified mortality curves
    base_rates = {
        'BROILER': {'0-7': 2.0, '8-21': 1.5, '22-35': 1.0, '36+': 0.5},
        'LAYER': {'0-7': 3.0, '8-21': 2.0, '22-35': 1.5, '36+': 1.0}
    }
    
    breed_rates = base_rates.get(breed, base_rates['BROILER'])
    
    if age_days <= 7:
        return breed_rates['0-7']
    elif age_days <= 21:
        return breed_rates['8-21']
    elif age_days <= 35:
        return breed_rates['22-35']
    else:
        return breed_rates['36+']


def get_fcr_benchmarks():
    """Get FCR benchmarks for different breeds"""
    return {
        'BROILER': {'excellent': 1.6, 'good': 1.8, 'fair': 2.0, 'poor': 2.2},
        'LAYER': {'excellent': 2.0, 'good': 2.2, 'fair': 2.4, 'poor': 2.6},
        'DUAL_PURPOSE': {'excellent': 1.8, 'good': 2.0, 'fair': 2.2, 'poor': 2.4}
    }


def get_survival_benchmarks():
    """Get survival benchmarks"""
    return {
        'BROILER': {'excellent': 97, 'good': 95, 'fair': 92, 'poor': 90},
        'LAYER': {'excellent': 95, 'good': 92, 'fair': 88, 'poor': 85},
        'DUAL_PURPOSE': {'excellent': 94, 'good': 91, 'fair': 87, 'poor': 84}
    }


def calculate_egg_production(batch):
    """Calculate egg production for layer batches"""
    if 'LAYER' not in batch.breed.upper():
        return 0
    
    # Get egg inventory for this batch
    egg_inventory = EggInventory.objects.filter(batch=batch)
    
    return egg_inventory.aggregate(
        total=Sum('quantity_trays')
    )['total'] or 0


def estimate_daily_weight_gain(batch, date):
    """Estimate daily weight gain for a specific date"""
    # This would use actual weighing records in practice
    # For now, we'll use breed-specific growth rates
    age_at_date = (date - batch.start_date).days
    weight_at_date = get_expected_weight(age_at_date, batch.breed)
    weight_previous_day = get_expected_weight(max(0, age_at_date - 1), batch.breed)
    
    return weight_at_date - weight_previous_day


def calculate_overall_fcr_trend(batches):
    """Calculate overall FCR trend across all batches"""
    # This would aggregate daily FCR data across all batches
    # For now, return a placeholder
    return {
        'trend': 'STABLE',
        'weekly_average': 1.9,
        'monthly_average': 1.95
    }


def calculate_overall_survival_trend(batches):
    """Calculate overall survival trend across all batches"""
    # This would aggregate daily survival data across all batches
    # For now, return a placeholder
    return {
        'trend': 'STABLE',
        'weekly_average': 94.5,
        'monthly_average': 93.8
    }


def get_mortality_causes_summary(batches):
    """Get summary of mortality causes across all batches"""
    all_causes = {}
    
    for batch in batches:
        causes = get_mortality_cause_analysis(batch)
        for cause, count in causes.items():
            all_causes[cause] = all_causes.get(cause, 0) + count
    
    return all_causes


def check_inventory_depletion_sync(batches):
    """Check inventory depletion synchronization"""
    sync_status = []
    
    for batch in batches:
        # Get feed inventory for this batch
        feed_inventory = InventoryItem.objects.filter(batch=batch, category='FEED')
        
        # Calculate expected vs actual depletion
        expected_depletion = FeedConsumption.objects.filter(batch=batch).aggregate(
            total=Sum('amount_consumed')
        )['total'] or 0
        
        actual_depletion = InventoryTransaction.objects.filter(
            item__in=feed_inventory,
            transaction_type='USAGE'
        ).aggregate(total=Sum('quantity_change'))['total'] or 0
        
        sync_percentage = (actual_depletion / expected_depletion * 100) if expected_depletion > 0 else 100
        
        sync_status.append({
            'batch_id': str(batch.id),
            'sync_percentage': sync_percentage,
            'status': 'GOOD' if sync_percentage >= 95 else 'POOR' if sync_percentage >= 80 else 'CRITICAL'
        })
    
    return sync_status


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


# Helper functions for performance trends

def get_weight_trends(batch):
    """Get weight trends for the batch"""
    # This would query weight records from a WeightRecord model
    # For now, return placeholder data based on age
    trends = []
    current_age = batch.current_age_days
    
    # Generate sample data points
    for days_ago in range(min(30, current_age), 0, -1):
        age = current_age - days_ago
        weight_per_bird = get_expected_weight(age, batch.breed)
        current_birds = batch.quantity - batch.mortality_count
        
        trends.append({
            'date': (timezone.now().date() - timedelta(days=days_ago)).isoformat(),
            'age_days': age,
            'weight_per_bird': weight_per_bird,
            'total_weight': weight_per_bird * current_birds,
            'sample_size': 10  # Placeholder
        })
    
    return trends


def get_fcr_trends(batch):
    """Get FCR trends for the batch"""
    trends = []
    current_age = batch.current_age_days
    
    # Generate sample FCR data
    for days_ago in range(min(30, current_age), 0, -1):
        date = (timezone.now().date() - timedelta(days=days_ago)).isoformat()
        
        # Get feed consumption for this period
        feed_consumed = get_feed_consumption_for_period(
            batch,
            date,
            date
        )
        
        # Estimate weight for this period
        age = current_age - days_ago
        weight_per_bird = get_expected_weight(age, batch.breed)
        current_birds = batch.quantity - batch.mortality_count
        total_weight = weight_per_bird * current_birds
        
        fcr = feed_consumed / total_weight if total_weight > 0 else 0
        
        trends.append({
            'date': date,
            'age_days': age,
            'feed_consumed': feed_consumed,
            'total_weight': total_weight,
            'fcr': fcr
        })
    
    return trends


def get_survival_trends(batch):
    """Get survival trends for the batch"""
    trends = []
    current_age = batch.current_age_days
    
    # Generate sample survival data
    for days_ago in range(min(30, current_age), 0, -1):
        date = (timezone.now().date() - timedelta(days=days_ago)).isoformat()
        
        # Get mortality records for this period
        mortality_records = HealthRecord.objects.filter(
            affected_batch=batch,
            record_type='MORTALITY',
            date=date
        )
        
        # Calculate cumulative mortality up to this point
        cumulative_mortality = mortality_records.count() * 5  # Placeholder: 5 birds per record
        
        survival_rate = ((batch.quantity - cumulative_mortality) / batch.quantity * 100) if batch.quantity > 0 else 100
        
        trends.append({
            'date': date,
            'cumulative_mortality': cumulative_mortality,
            'survival_rate': survival_rate,
            'daily_mortality': mortality_records.count()
        })
    
    return trends


def get_feed_consumption_trends(batch):
    """Get feed consumption trends for the batch"""
    trends = []
    current_age = batch.current_age_days
    
    # Generate sample feed consumption data
    for days_ago in range(min(30, current_age), 0, -1):
        date = (timezone.now().date() - timedelta(days=days_ago)).isoformat()
        
        # Get feed consumption for this period
        feed_consumed = get_feed_consumption_for_period(
            batch,
            date,
            date
        )
        
        trends.append({
            'date': date,
            'feed_consumed': feed_consumed,
            'feed_per_bird': feed_consumed / (batch.quantity - batch.mortality_count) if (batch.quantity - batch.mortality_count) > 0 else 0
        })
    
    return trends


def get_inventory_depletion_trends(batch):
    """Get inventory depletion trends for the batch"""
    trends = []
    current_age = batch.current_age_days
    
    # Get feed inventory items for this batch
    feed_inventory = InventoryItem.objects.filter(batch=batch, category='FEED')
    
    # Generate sample inventory depletion data
    for days_ago in range(min(30, current_age), 0, -1):
        date = (timezone.now().date() - timedelta(days=days_ago)).isoformat()
        
        # Get inventory transactions for this period
        inventory_transactions = InventoryTransaction.objects.filter(
            item__in=feed_inventory,
            transaction_type='USAGE',
            created_at__date=date
        )
        
        depletion = inventory_transactions.aggregate(
            total=Sum('quantity_change')
        )['total'] or 0
        
        trends.append({
            'date': date,
            'inventory_depletion': abs(depletion),  # Make positive
            'transaction_count': inventory_transactions.count()
        })
    
    return trends


def calculate_performance_correlations(batch):
    """Calculate correlations between different performance metrics"""
    # This would analyze correlations between weight, FCR, survival, etc.
    # For now, return placeholder correlations
    return {
        'weight_fcr_correlation': -0.85,  # Negative correlation: higher weight = lower FCR
        'feed_consumption_weight_correlation': 0.92,  # Positive correlation
        'mortality_fcr_correlation': 0.45,  # Positive correlation: higher mortality = higher FCR
        'survival_weight_correlation': 0.78,  # Positive correlation: higher survival = higher weight
        'age_fcr_correlation': 0.65  # Positive correlation: older birds = different FCR
    }


def calculate_performance_summary(batch):
    """Calculate overall performance summary for a batch"""
    current_birds = batch.quantity - batch.mortality_count
    survival_rate = (current_birds / batch.quantity * 100) if batch.quantity > 0 else 0
    
    # Get current metrics
    total_feed_consumed = FeedConsumption.objects.filter(batch=batch).aggregate(
        total=Sum('amount_consumed')
    )['total'] or 0
    
    estimated_weight = estimate_batch_weight(batch)
    current_fcr = total_feed_consumed / estimated_weight if estimated_weight > 0 else 0
    
    # Calculate performance score
    fcr_score = max(0, 100 - (current_fcr - 1.8) * 20)  # Target FCR = 1.8
    survival_score = survival_rate
    growth_score = min(100, (estimated_weight / current_birds) * 10) if current_birds > 0 else 0
    
    overall_score = (fcr_score * 0.4 + survival_score * 0.4 + growth_score * 0.2)
    
    return {
        'overall_score': overall_score,
        'key_metrics': {
            'fcr': current_fcr,
            'survival_rate': survival_rate,
            'average_weight_per_bird': estimated_weight / current_birds if current_birds > 0 else 0,
            'total_feed_consumed': total_feed_consumed
        },
        'performance_rating': get_performance_rating(overall_score),
        'recommendations': get_performance_recommendations(current_fcr, survival_rate, overall_score)
    }


def get_performance_rating(score):
    """Get performance rating based on score"""
    if score >= 90:
        return 'EXCELLENT'
    elif score >= 80:
        return 'GOOD'
    elif score >= 70:
        return 'FAIR'
    else:
        return 'POOR'


def get_performance_recommendations(fcr, survival_rate, score):
    """Get performance recommendations based on metrics"""
    recommendations = []
    
    if fcr > 2.0:
        recommendations.append('Review feed quality and feeding schedule')
        recommendations.append('Check for health issues affecting feed conversion')
    
    if survival_rate < 90:
        recommendations.append('Improve biosecurity measures')
        recommendations.append('Review environmental conditions')
        recommendations.append('Consult with veterinarian for health issues')
    
    if score < 70:
        recommendations.append('Comprehensive performance review needed')
        recommendations.append('Consider management practice changes')
    elif score < 85:
        recommendations.append('Monitor performance trends closely')
        recommendations.append('Optimize feeding and health management')
    
    return recommendations
