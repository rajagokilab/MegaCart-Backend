import os
import django
from django.core.files import File

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from product_app.models import Product, Category

def migrate_model_images(model_class, type_name):
    print(f"\n--- Processing {type_name} ---")
    items = model_class.objects.all()

    for item in items:
        if not item.image:
            print(f"Skipping {item.name} (No image)")
            continue

        if str(item.image).startswith("http"):
            print(f"Skipping {item.name} (Already on Cloudinary)")
            continue

        filename = os.path.basename(str(item.image))
        local_path = os.path.join(os.getcwd(), "media", str(item.image))

        if os.path.exists(local_path):
            print(f"Uploading: {item.name}...")
            with open(local_path, 'rb') as f:
                item.image.save(filename, File(f), save=True)
            print(f"✅ Success! New URL: {item.image.url}")
        else:
            print(f"❌ File missing on laptop: {local_path}")

if __name__ == "__main__":
    migrate_model_images(Product, "Products")
    migrate_model_images(Category, "Categories")
    print("\n✅ Migration Complete!")
