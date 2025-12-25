import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Now we can import models
try:
    from django.db import connection
    
    # Test database connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print("Database connection successful!" if result and result[0] == 1 else "Database connection failed!")
    
    # Test model imports
    from farms.models import Farm, Batch
    from inventory.models import Inventory, InventoryItem, InventoryTransaction
    print("All models imported successfully!")
    
    # Test if we can query the database
    try:
        print(f"Number of farms: {Farm.objects.count()}")
        print(f"Number of batches: {Batch.objects.count()}")
        print(f"Number of inventories: {Inventory.objects.count()}")
        print(f"Number of inventory items: {InventoryItem.objects.count()}")
        print(f"Number of transactions: {InventoryTransaction.objects.count()}")
    except Exception as e:
        print(f"Error querying database: {e}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
