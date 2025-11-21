import os
import django
import cloudinary.uploader

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from product_app.models import Category

categories = Category.objects.all()

for cat in categories:
    if not cat.image:
        print(f"No image for {cat.name}, skipping.")
        continue

    if cat.cloudinary_url:
        print(f"Already uploaded: {cat.name}, skipping.")
        continue

    local_path = os.path.join(os.getcwd(), "media", str(cat.image))
    if os.path.exists(local_path):
        print(f"Uploading {cat.name}...")
        result = cloudinary.uploader.upload(local_path, folder="category_images")
        cat.cloudinary_url = result["secure_url"]
        cat.save()
        print(f"Uploaded: {cat.cloudinary_url}")
    else:
        print(f"Local file missing for {cat.name}: {local_path}")

print("✅ All done!")
