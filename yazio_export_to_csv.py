
import json
import csv
import subprocess
import os

# Configuration
EMAIL = input("📧 Enter your Yazio email: ").strip()
PASSWORD = input("🔐 Enter your Yazio password: ").strip()
EXPORTER_PATH = "/root/Yazio-Exporter/YazioExport"
TOKEN_FILE = "token.txt"
DAYS_FILE = "days.json"
PRODUCTS_FILE = "products.json"
DETAIL_CSV = "nutrition_log.csv"
MEAL_SUMMARY_CSV = "meal_summary.csv"
DAILY_SUMMARY_CSV = "daily_summary.csv"

# Login
print("🔑 Logging in to Yazio...")
subprocess.run([EXPORTER_PATH, "login", EMAIL, PASSWORD, "--out", TOKEN_FILE], check=True)

# Export diary data
print("📅 Exporting diary data...")
subprocess.run([EXPORTER_PATH, "days", "--token", TOKEN_FILE, "--what", "all", "--from", "2025-01-01", "--to", "2025-12-31", "--out", DAYS_FILE], check=True)

# Export product data
print("📦 Exporting product data...")
subprocess.run([EXPORTER_PATH, "products", "--token", TOKEN_FILE, "--from", DAYS_FILE, "-o", PRODUCTS_FILE], check=True)

# Helpers
def fix_encoding(name):
    try:
        return name.encode('latin1').decode('utf-8')
    except:
        return name

def calc_total_kcal(amount, kcal_per_gram):
    try:
        return round(float(amount) * float(kcal_per_gram), 2)
    except:
        return 0.0

# Load data
with open(DAYS_FILE, 'r', encoding='utf-8') as f:
    days_data = json.load(f)

with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
    products_data = json.load(f)

product_lookup = {pid: pdata for pid, pdata in products_data.items()}
rows = []
summary_by_meal = {}
summary_by_day = {}

# Process entries
for date, content in days_data.items():
    consumed = content.get('consumed')
    if not consumed or not isinstance(consumed, dict):
        continue

    products = consumed.get('products', [])
    if not isinstance(products, list):
        continue

    for item in products:
        if not isinstance(item, dict):
            continue

        product_id = item.get('product_id', '')
        product = product_lookup.get(product_id, {})
        name = fix_encoding(product.get('name', 'Unknown'))
        nutrients = product.get('nutrients', {})

        kcal_g = float(nutrients.get('energy.energy', 0) or 0)
        protein_g = float(nutrients.get('nutrient.protein', 0) or 0)
        fat_g = float(nutrients.get('nutrient.fat', 0) or 0)
        carbs_g = float(nutrients.get('nutrient.carb', 0) or 0)
        amount = float(item.get('amount', 0) or 0)

        total_kcal = calc_total_kcal(amount, kcal_g)
        total_protein = round(amount * protein_g, 2)
        total_fat = round(amount * fat_g, 2)
        total_carbs = round(amount * carbs_g, 2)

        meal_type = item.get('daytime', 'unknown')
        key_meal = (date, meal_type)
        key_day = date

        if key_meal not in summary_by_meal:
            summary_by_meal[key_meal] = 0.0
        summary_by_meal[key_meal] += total_kcal

        if key_day not in summary_by_day:
            summary_by_day[key_day] = {'kcal': 0.0, 'protein': 0.0, 'fat': 0.0, 'carbs': 0.0}
        summary_by_day[key_day]['kcal'] += total_kcal
        summary_by_day[key_day]['protein'] += total_protein
        summary_by_day[key_day]['fat'] += total_fat
        summary_by_day[key_day]['carbs'] += total_carbs

        rows.append({
            'Date': date,
            'Time': item.get('date', ''),
            'Meal': meal_type,
            'Product': name,
            'Amount': amount,
            'Unit': item.get('serving', ''),
            'Portions': item.get('serving_quantity', ''),
            'Calories/g': kcal_g,
            'Calories total': total_kcal,
            'Protein/g': protein_g,
            'Fat/g': fat_g,
            'Carbs/g': carbs_g,
            'Protein total': total_protein,
            'Fat total': total_fat,
            'Carbs total': total_carbs
        })

# Write CSV files
with open(DETAIL_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

with open(MEAL_SUMMARY_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Date', 'Meal', 'Calories total'])
    for (date, meal), total in sorted(summary_by_meal.items()):
        writer.writerow([date, meal, round(total, 2)])

with open(DAILY_SUMMARY_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Date', 'Calories total', 'Protein total', 'Fat total', 'Carbs total'])
    for date, data in sorted(summary_by_day.items()):
        writer.writerow([
            date,
            round(data['kcal'], 2),
            round(data['protein'], 2),
            round(data['fat'], 2),
            round(data['carbs'], 2)
        ])

print("✅ CSV files created:")
print(f" - {DETAIL_CSV}")
print(f" - {MEAL_SUMMARY_CSV}")
print(f" - {DAILY_SUMMARY_CSV}")
