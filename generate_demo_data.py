import pandas as pd
import random
import os

def generate_linkedin_demo(path, n=50):
    data = []
    statuses = ["ACTIVE", "PAUSED", "ARCHIVED", "paused", "active"] # mix in some to-be-fixed values
    for i in range(n):
        headline = f"Headline {i}: " + ("This is very long " * 5 if i % 10 == 0 else "Quality Ad")
        data.append({
            "Campaign Name": f"LI_Campaign_{random.randint(100, 999)}",
            "Status": random.choice(statuses),
            "Headline": headline[:100] if i % 10 == 0 else headline,
            "Introduction": f"Introduction for ad {i} with some context.",
            "Daily Budget": random.randint(10, 500)
        })
    df = pd.DataFrame(data)
    df.to_csv(path, index=False)
    print(f"Generated {path}")

def generate_google_demo(path, n=50):
    data = []
    statuses = ["Enabled", "Paused", "Removed", "active", "paused"]
    for i in range(n):
        data.append({
            "Campaign": f"G_Search_Campaign_{random.randint(10, 99)}",
            "Ad Group": f"AdGroup_{random.choice(['A', 'B', 'C'])}",
            "Keyword": f"keyword_{i}",
            "Status": random.choice(statuses),
            "Max CPC": round(random.uniform(0.5, 5.0), 2)
        })
    df = pd.DataFrame(data)
    df.to_csv(path, index=False)
    print(f"Generated {path}")

def generate_meta_demo(path, n=50):
    data = []
    statuses = ["ACTIVE", "PAUSED", "ARCHIVED"]
    for i in range(n):
        body = f"Discover our new winter collection! Ad number {i} is here to show you the best deals."
        if i % 15 == 0:
            body = body * 3 # Make it too long
        data.append({
            "Campaign Name": "Meta_Conver_2026",
            "Ad Set Name": f"Targeting_{random.choice(['US', 'UK', 'CA'])}",
            "Ad Name": f"Ad_Creative_{i}",
            "Campaign Status": random.choice(statuses),
            "Body": body,
            "Title": f"Title {i}"[:50]
        })
    df = pd.DataFrame(data)
    df.to_csv(path, index=False)
    print(f"Generated {path}")

if __name__ == "__main__":
    os.makedirs("samples", exist_ok=True)
    generate_linkedin_demo("samples/linkedin_demo_50.csv")
    generate_google_demo("samples/google_demo_50.csv")
    generate_meta_demo("samples/meta_demo_50.csv")
