import urllib.request
import os

# URLs for Bootstrap files
bootstrap_css_url = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
bootstrap_icons_url = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css"

# Directory to save files
static_css_dir = r"d:\THE CEO\Bossin\finance-committe-app\static\css"

# Download Bootstrap CSS
print("Downloading Bootstrap CSS...")
urllib.request.urlretrieve(bootstrap_css_url, os.path.join(static_css_dir, "bootstrap.min.css"))
print("Bootstrap CSS downloaded successfully!")

# Download Bootstrap Icons
print("Downloading Bootstrap Icons...")
urllib.request.urlretrieve(bootstrap_icons_url, os.path.join(static_css_dir, "bootstrap-icons.css"))
print("Bootstrap Icons downloaded successfully!")

print("All files downloaded!")
