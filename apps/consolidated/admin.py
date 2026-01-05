from django.contrib import admin
from .models import (
    User, Batch, BreedConfiguration, Farm, Subscription, 
    SubscriptionPlan, FarmerProfile, BreedStage, BreedMilestone,
    Device, Recommendation, Payment, UserFeatureAccess, Alert, Activity,
    InventoryItem, InventoryTransaction, HealthRecord,
    MedicineInventory, MedicineAdministration, EquipmentInventory,
    LaborRecord, ServiceExpense, HealthAlert, EggInventory, EggSale
)

# Existing registers
admin.site.register(User)
admin.site.register(Batch)
admin.site.register(BreedConfiguration)
admin.site.register(Farm)
admin.site.register(Subscription)
admin.site.register(SubscriptionPlan)
admin.site.register(FarmerProfile)
admin.site.register(BreedStage)
admin.site.register(BreedMilestone)
admin.site.register(Device)
admin.site.register(Recommendation)
admin.site.register(Payment)
admin.site.register(UserFeatureAccess)
admin.site.register(Alert)
admin.site.register(Activity)
admin.site.register(InventoryItem)
admin.site.register(InventoryTransaction)
admin.site.register(HealthRecord)

# New inventory models registration
@admin.register(MedicineInventory)
class MedicineInventoryAdmin(admin.ModelAdmin):
    list_display = ('inventory_item', 'medicine_type', 'vaccine_type', 'dosage', 'administration_route')
    list_filter = ('medicine_type', 'vaccine_type', 'administration_route')
    search_fields = ('inventory_item__name', 'purpose')

@admin.register(MedicineAdministration)
class MedicineAdministrationAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'batch', 'administered_date', 'number_of_birds', 'administered_by')
    list_filter = ('administered_date',)
    search_fields = ('medicine__inventory_item__name', 'batch__batch_name', 'reason')

@admin.register(EquipmentInventory)
class EquipmentInventoryAdmin(admin.ModelAdmin):
    list_display = ('inventory_item', 'equipment_type', 'condition', 'purchase_cost', 'next_maintenance_date')
    list_filter = ('equipment_type', 'condition', 'replacement_alert')
    search_fields = ('inventory_item__name', 'serial_number')

@admin.register(LaborRecord)
class LaborRecordAdmin(admin.ModelAdmin):
    list_display = ('worker_name', 'role', 'worker_type', 'wage_amount', 'payment_frequency', 'is_active')
    list_filter = ('worker_type', 'payment_frequency', 'is_active')
    search_fields = ('worker_name', 'role', 'phone_number')

@admin.register(ServiceExpense)
class ServiceExpenseAdmin(admin.ModelAdmin):
    list_display = ('service_type', 'service_provider', 'cost', 'service_date')
    list_filter = ('service_type', 'service_date')
    search_fields = ('service_provider', 'description')

@admin.register(HealthAlert)
class HealthAlertAdmin(admin.ModelAdmin):
    list_display = ('batch', 'alert_type', 'severity', 'detected_at', 'resolved')
    list_filter = ('alert_type', 'severity', 'resolved')
    search_fields = ('batch__batch_name', 'message')

@admin.register(EggInventory)
class EggInventoryAdmin(admin.ModelAdmin):
    list_display = ('batch', 'collection_date', 'grade', 'quality', 'quantity_trays', 'available_stock', 'price_per_tray')
    list_filter = ('grade', 'quality', 'collection_date')
    search_fields = ('batch__batch_name',)

@admin.register(EggSale)
class EggSaleAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'customer_type', 'quantity_sold', 'total_amount', 'sale_date', 'payment_status')
    list_filter = ('customer_type', 'payment_status', 'sale_date')
    search_fields = ('customer_name', 'customer_phone', 'invoice_number')

