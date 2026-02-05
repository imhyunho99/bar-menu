import csv
from django.core.management.base import BaseCommand
from menu.models import Category, MenuItem
import os

class Command(BaseCommand):
    help = 'Imports or updates menu items for a specific category from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file_path', type=str, help='The path to the CSV file to import.')
        parser.add_argument(
            '--category',
            type=str,
            help='Specify the parent category to update (e.g., "위스키"). This will delete all existing items in that parent category before importing.'
        )

    def handle(self, *args, **options):
        csv_file_path = options['csv_file_path']
        target_parent_category_name = options['category']

        if not target_parent_category_name:
            self.stdout.write(self.style.ERROR("Please specify a parent category to update using the --category option."))
            self.stdout.write(self.style.WARNING("Example: python manage.py import_csv path/to/data.csv --category \"위스키\""))
            return

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"File not found at: {csv_file_path}"))
            return

        # --- Deletion Step ---
        self.stdout.write(self.style.WARNING(f"Preparing to delete all existing menu items under the parent category '{target_parent_category_name}'..."))
        try:
            parent_category = Category.objects.get(name=target_parent_category_name, parent=None)
            # Get all child categories of the parent
            child_categories = parent_category.sub_categories.all()
            # Delete all menu items within those child categories
            items_to_delete = MenuItem.objects.filter(category__in=child_categories)
            count = items_to_delete.count()
            if count > 0:
                items_to_delete.delete()
                self.stdout.write(self.style.SUCCESS(f"Successfully deleted {count} old menu item(s) from '{target_parent_category_name}'."))
            else:
                self.stdout.write(self.style.NOTICE(f"No existing menu items found for '{target_parent_category_name}' to delete."))
        except Category.DoesNotExist:
            self.stdout.write(self.style.NOTICE(f"Parent category '{target_parent_category_name}' not found. No items will be deleted. New items will be created under it."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred during deletion: {e}"))
            return
        
        # --- Import Step ---
        self.stdout.write(self.style.NOTICE(f"Starting to import items for '{target_parent_category_name}' from {csv_file_path}..."))
        with open(csv_file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file, delimiter=',')
            
            items_created = 0
            items_updated = 0

            for row in reader:
                parent_category_name = row.get('대분류', '').strip()

                # Process only the rows that match the target parent category
                if parent_category_name == target_parent_category_name:
                    category_name = row.get('소분류', '').strip()
                    item_name_en = row.get('영문명', '').strip()
                    item_name_ko = row.get('한글명', '').strip()
                    item_price = row.get('가격', '').strip()
                    item_description = row.get('설명', '').strip()

                    if not all([category_name, item_name_ko, item_price]):
                        self.stdout.write(self.style.WARNING(f"Skipping row due to missing data: {row}"))
                        continue

                    # Get or create parent category
                    parent_cat, _ = Category.objects.get_or_create(name=parent_category_name, parent=None)

                    # Get or create child category
                    child_cat, _ = Category.objects.get_or_create(name=category_name, parent=parent_cat)

                    # Create or update menu item
                    menu_item, created = MenuItem.objects.update_or_create(
                        name=item_name_ko,
                        category=child_cat,
                        defaults={
                            'name_en': item_name_en,
                            'price': item_price,
                            'description': item_description,
                        }
                    )

                    if created:
                        items_created += 1
                    else:
                        items_updated += 1
        
        self.stdout.write(self.style.SUCCESS(f"Import for '{target_parent_category_name}' complete."))
        self.stdout.write(self.style.SUCCESS(f"Created: {items_created} new items. Updated: {items_updated} existing items."))
