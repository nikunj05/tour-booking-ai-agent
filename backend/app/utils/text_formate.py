import re
from bs4 import BeautifulSoup 

def slugify(text: str):
    """
    Converts a string to a URL-friendly slug.
    """
    text = text.lower().strip()
    # Replace non-alphanumeric characters with hyphens
    text = re.sub(r'[^a-z0-9]+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text

def format_package_text(package: dict):
    # 1️⃣ Get text description without HTML
    description = package.get("description", "Amazing tour experience")
    
    # Remove HTML tags
    description = BeautifulSoup(description, "html.parser").get_text(separator="\n")
    
    # 2️⃣ Format itinerary
    itinerary_text = ""
    itinerary_html = package.get("itinerary", "")
    
    if itinerary_html:
        # Remove HTML tags and create bullets
        itinerary_items = BeautifulSoup(itinerary_html, "html.parser").find_all("li")
        itinerary_text = "\n".join([f"• {i.get_text().strip()}" for i in itinerary_items])

    excludes_text = ""
    excludes_html = package.get("excludes", "")
    
    if excludes_html:
        # Remove HTML tags and create bullets
        excludes_items = BeautifulSoup(excludes_html, "html.parser").find_all("li")
        excludes_text = "\n".join([f"• {i.get_text().strip()}" for i in excludes_items])
    
    # 3️⃣ Final text for WhatsApp
    text = f"""🏷️ *{package['name']}*

✨ {description}

🗺️ *Itinerary*
{itinerary_text}

❌ *Excludes*
{excludes_text}

💰 *Price:* {package['currency']} {package['price']} per adult"""
    
    return text