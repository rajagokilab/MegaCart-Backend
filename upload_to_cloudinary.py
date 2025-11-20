import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")  # adjust if your settings are elsewhere
django.setup()

import cloudinary.uploader
from product_app.models import Product

products = Product.objects.all()

for product in products:
    if not product.image:
        print("No image:", product.name)
        continue

    if str(product.image).startswith("http"):
        print("Already a URL, skipping:", product.name)
        continue

    local_path = os.path.join(os.getcwd(), "media", str(product.image))

    if os.path.exists(local_path):
        print("Uploading:", product.name)
        result = cloudinary.uploader.upload(local_path, folder="product_images")
        product.image_url = result["secure_url"]
        product.save()
        print("Uploaded:", product.image_url)
    else:
        print("Local file missing:", local_path)

print("Done!")
