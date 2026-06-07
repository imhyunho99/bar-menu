# menu/management/commands/convert_to_webp.py
import os
from django.core.management.base import BaseCommand
from menu.models import Category, MenuItem, SiteSettings
from menu.utils import optimize_image

class Command(BaseCommand):
    help = 'Converts all existing Category, MenuItem, and SiteSettings JPG/PNG images in the database to WebP format.'

    def convert_field(self, instance, field_name, max_width, quality):
        field = getattr(instance, field_name)
        if not field or not field.name:
            return False
            
        if field.name.lower().endswith('.webp'):
            return False
            
        self.stdout.write(f"Converting {instance.__class__.__name__} (ID: {instance.id}) - {field_name}: {field.name}")
        try:
            # optimize_image will handle conversion to webp
            optimized_file = optimize_image(field, max_width=max_width, quality=quality)
            
            # Set the optimized file back to the instance field
            setattr(instance, field_name, optimized_file)
            return True
        except Exception as e:
            self.stderr.write(f"Error converting {field.name}: {e}")
            return False

    def handle(self, *args, **options):
        self.stdout.write("Starting WebP Conversion of existing images...")
        
        # 1. Category images
        for cat in Category.objects.all():
            if self.convert_field(cat, 'category_image', max_width=600, quality=80):
                cat.save()
                self.stdout.write(self.style.SUCCESS(f"-> Saved Category: {cat.name}"))
                
        # 2. MenuItem images
        for item in MenuItem.objects.all():
            updated = False
            if self.convert_field(item, 'menu_image', max_width=800, quality=80):
                updated = True
            if self.convert_field(item, 'detail_image', max_width=1200, quality=85):
                updated = True
                
            if updated:
                item.save()
                self.stdout.write(self.style.SUCCESS(f"-> Saved MenuItem: {item.name}"))
                
        # 3. SiteSettings images
        for settings in SiteSettings.objects.all():
            updated = False
            if self.convert_field(settings, 'logo_image', max_width=192, quality=90):
                updated = True
            if self.convert_field(settings, 'intro_image', max_width=1200, quality=85):
                updated = True
            if self.convert_field(settings, 'side_image', max_width=800, quality=85):
                updated = True
                
            if updated:
                settings.save()
                if settings.restaurant:
                    self.stdout.write(self.style.SUCCESS(f"-> Saved SiteSettings for {settings.restaurant.name}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"-> Saved SiteSettings (ID: {settings.id})"))

        self.stdout.write(self.style.SUCCESS("\nWebP Conversion Completed Successfully!"))
