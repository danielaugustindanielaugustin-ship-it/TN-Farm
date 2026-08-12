"""TNFarm AI helpers.

This app keeps AI access safe by default:
- if no API key is configured, it runs entirely offline
- if an OpenAI-compatible key is configured, it uses it only for prompt completion
- the model is explicitly blocked from filesystem/database access
"""
import json
import os
import random
import re
import urllib.error
import urllib.request

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def _llm_fallback(message: str, default_reply: str) -> str:
    if not OPENAI_API_KEY:
        return default_reply

    url = f"{OPENAI_API_BASE}/chat/completions"
    system_prompt = (
        "You are a helpful TNFarm assistant for a farm marketplace app. "
        "Answer using only the user request and public app knowledge. "
        "Never claim database or file-system access. Do not access or expose secrets, "
        "private records, or raw user data."
    )
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
        "temperature": 0.4,
        "max_tokens": 220,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)
            return (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip() or default_reply
            )
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, json.JSONDecodeError):
        return default_reply


# ---------------------------------------------------------------------
# 1. CHATBOT — FAQ knowledge base (English + Tamil keyword matching)
# ---------------------------------------------------------------------

FAQ_RULES = [
    {
        "keywords": ["what is tnfarm", "about tnfarm", "tnfarm"],
        "reply": "TNFarm is a farmer discovery and social commerce platform for Tamil Nadu. "
                 "Customers can search farms, browse products, follow farms, message farmers, "
                 "and leave reviews. Farmers can create profiles, add products, post updates, "
                 "and connect directly with buyers.",
    },
    {
        "keywords": ["how to use", "how do i use", "how use", "what can i do", "features", "how it works", "use tnfarm", "how to use tnfarm"],
        "reply": "Use TNFarm to discover farms and products across Tamil Nadu. Search by farm name, village, or district on the home page, visit farm profiles to view products and reviews, follow farms for updates, and message farmers directly from their profile.",
    },
    {
        "keywords": ["register", "sign up", "signup", "join", "create account", "பதிவு"],
        "reply": "To register: click 'Login' in the top menu, then choose 'Join as Farmer' "
                 "or 'Join as Customer'. Fill in your details, and farmers will also add farm info "
                 "like village, district, and pincode during signup.",
    },
    {
        "keywords": ["login", "sign in", "email", "password", "account access"],
        "reply": "Use the Login page to sign in with your registered email and password. "
                 "If you don't have an account yet, choose 'Join as Farmer' or 'Join as Customer'.",
    },
    {
        "keywords": ["farmer", "sell", "become a farmer", "vendor", "seller", "விவசாயி"],
        "reply": "Farmers can add products from Dashboard → '+ Add Product', publish posts on the Feed, "
                 "and receive messages from customers. Your farm profile is visible to people on the home page.",
    },
    {
        "keywords": ["product", "products", "produce", "item", "buy", "selling"],
        "reply": "Browse all available products on the Products page, or visit a farm profile to see its full product list. "
                 "Each product page shows price, unit, availability, and the farm that sells it.",
    },
    {
        "keywords": ["search", "filter", "district", "village", "location", "மாவட்டம்"],
        "reply": "Use the home page search bar to find farms by name, village, or district. "
                 "You can also filter farms by district to discover nearby producers.",
    },
    {
        "keywords": ["farm profile", "profile", "rating", "reviews", "followers", "follow"],
        "reply": "A farm profile shows the farm's description, products, recent posts, reviews, and location. "
                 "You can follow a farm for updates, leave a review, or message the farmer directly.",
    },
    {
        "keywords": ["message", "chat", "contact", "talk", "contact farmer", "customer support"],
        "reply": "Open a farm profile and click 'Message' to chat directly with the farmer. "
                 "This is the best way to ask about availability, pickup, or order details.",
    },
    {
        "keywords": ["follow", "following", "followed", "followers", "updates"],
        "reply": "When you follow a farm, you can see its updates and stay connected to new products and posts. "
                 "Following also helps you remember farms you like.",
    },
    {
        "keywords": ["review", "rating", "stars", "feedback", "comment"],
        "reply": "You can submit a star rating and written review on any farm's profile page. "
                 "Reviews help other buyers learn about the farm's quality and service.",
    },
    {
        "keywords": ["organic", "certified", "in-conversion", "chemical-free", "இயற்கை"],
        "reply": "Farms can report their organic status as Certified, In-Conversion, or Not Certified. "
                 "Products may also be specifically marked as organic when added by a farmer.",
    },
    {
        "keywords": ["dashboard", "my farm", "my products", "farmer dashboard", "customer dashboard"],
        "reply": "Farmers see their farm profile stats, products, posts, followers, and reviews on the Dashboard. "
                 "Customers see the farms they follow and the reviews they've written.",
    },
    {
        "keywords": ["notifications", "alerts", "update"],
        "reply": "The Notifications page shows you new followers, messages, reviews, and other updates related to your account.",
    },
    {
        "keywords": ["payment", "delivery", "order online", "pay", "cash"],
        "reply": "TNFarm currently helps you discover farms and connect directly with farmers. "
                 "Payment and delivery are arranged privately between you and the farmer outside the platform.",
    },
    {
        "keywords": ["thank", "thanks", "thanks!", "tnx", "நன்றி"],
        "reply": "You're welcome! 🌿 Ask me anything else about TNFarm or how to use the site.",
    },
]

FALLBACK_REPLIES = [
    "I don't have the exact answer yet, but you can ask me about registering, farms, products, or messaging farmers.",
    "Try asking about a TNFarm feature like Home, Products, Dashboard, or Farm Profiles, and I'll help explain it.",
    "If you're unsure, ask me how to use the search bar, follow a farm, or leave a review on TNFarm.",
]


def _normalize_text(message: str) -> str:
    return re.sub(r"[^\w\s]+", " ", (message or "").strip().lower())


def chatbot_reply(message: str) -> str:
    text = _normalize_text(message)
    if not text:
        return "Ask me anything about TNFarm — registration, farms, products, or orders!"

    for rule in FAQ_RULES:
        if any(kw in text for kw in rule["keywords"]):
            return rule["reply"]

    default_reply = random.choice(FALLBACK_REPLIES)
    return _llm_fallback(message, default_reply)


# ---------------------------------------------------------------------
# 2. AI PRODUCT DESCRIPTION SUGGESTIONS
# ---------------------------------------------------------------------

_OPENERS = [
    "Freshly harvested {name}, grown with care on our farm.",
    "Farm-fresh {name} picked at peak ripeness for the best flavour.",
    "Locally grown {name}, straight from our fields to your kitchen.",
]

_ORGANIC_LINE = "Grown using organic, chemical-free farming practices."
_NON_ORGANIC_LINE = "Grown using traditional farming methods passed down through generations."

_CATEGORY_LINES = {
    "vegetables": "Perfect for everyday home cooking and packed with nutrients.",
    "fruits": "Naturally sweet and juicy — a healthy addition to your daily diet.",
    "seeds": "High-quality seeds, carefully selected and cleaned for best germination.",
    "flowers": "Fresh-cut flowers, ideal for home decor or special occasions.",
    "milk & dairy": "Delivered fresh for the best taste and nutrition.",
    "organic specials": "A specially curated organic product from our farm.",
}


def suggest_product_description(name: str, category_name: str = "", is_organic: bool = False) -> str:
    name = (name or "our produce").strip()
    if not name:
        return "Fresh farm produce, carefully grown and packed for you."

    base_text = f"Create a short product description for {name} in a farm marketplace. Keep it friendly, concise, and sales-focused."
    if category_name:
        base_text += f" Category: {category_name}."
    if is_organic:
        base_text += " Mark it as organic."

    default_description = " ".join(
        [
            random.choice(_OPENERS).format(name=name),
            _ORGANIC_LINE if is_organic else _NON_ORGANIC_LINE,
            _CATEGORY_LINES.get((category_name or "").strip().lower(), "Freshly picked and ready to enjoy."),
            "Contact us for bulk orders or farm visits!",
        ]
    )
    return _llm_fallback(base_text, default_description)


# ---------------------------------------------------------------------
# 3. AI POST CAPTION SUGGESTIONS
# ---------------------------------------------------------------------

_CAPTION_TEMPLATES = [
    "Another beautiful day on the farm 🌾 Grateful for the harvest today!",
    "Fresh from the fields to your table 🥬 Nothing beats farm-fresh produce.",
    "Hard work and good soil — that's the TNFarm way 🌱",
    "Harvest season is here! Come visit us or check out what's fresh today 🍅",
    "Sharing a glimpse of life on our farm today 🌿 #TNFarm",
]


def suggest_post_caption(location: str = "") -> str:
    prompt = "Write a short upbeat farm social media caption for a post. Keep it warm, natural, and agricultural."
    if location:
        prompt += f" Include the location: {location}."

    default_caption = random.choice(_CAPTION_TEMPLATES)
    if location:
        default_caption += f" 📍 {location}"
    return _llm_fallback(prompt, default_caption)
