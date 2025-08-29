import requests
import pandas as pd
from bs4 import BeautifulSoup

# Constants
RATE_SLEEP = 0.5  # pause between requests
HEADERS_TM = {"User-Agent": "Mozilla/5.0"}

# -------------------- User Interaction --------------------
def select_competition():
    while True:
        print("Select competition:")
        print("1. Champions League")
        print("2. Europa League")
        print("3. Conference League")
        choice = input("Enter 1, 2, or 3: ").strip()

        if choice == "1":
            return "CL", "Champions League"
        elif choice == "2":
            return "EL", "Europa League"
        elif choice == "3":
            return "UCOL", "Conference League"
        else:
            print("Invalid choice. Please enter 1, 2, or 3.\n")

# -------------------- Data Scraping --------------------
def scrape_tm_team_values(tm_url):
    resp = requests.get(tm_url, headers=HEADERS_TM)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    teams_values = {}
    rows = soup.select("table.items tr")
    for row in rows:
        name_link = row.select_one("td.hauptlink a")
        mv_td = row.select_one("td.rechts")
        if name_link and mv_td:
            tm_name = name_link.text.strip()
            mv_text = mv_td.text.strip().replace("€", "").lower()
            if "bn" in mv_text:
                value = float(mv_text.replace("bn", "").replace(",", ".")) * 1000
            elif "m" in mv_text:
                value = float(mv_text.replace("m", "").replace(",", "."))
            else:
                value = float(mv_text.replace(",", "."))
            teams_values[tm_name] = round(value, 2)
    return teams_values

def scrape_tm_fixtures(fixtures_url):
    resp = requests.get(fixtures_url, headers=HEADERS_TM)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    opp_map = {}
    rows = soup.select("tbody tr")
    for row in rows:
        home_a = row.select_one("td.text-right.hauptlink a")
        away_a = row.select_one("td.no-border-links.hauptlink a")
        if home_a and away_a:
            home = home_a.get("title").strip()
            away = away_a.get("title").strip()
            opp_map.setdefault(home, set()).add(away)
            opp_map.setdefault(away, set()).add(home)
    return opp_map

# -------------------- Calculation --------------------
def calculate_opponent_info(opp_map, values):
    rows = []
    for team, opponents in opp_map.items():
        # Sort opponents by market value descending
        sorted_opponents = sorted(
            [o for o in opponents if values.get(o, 0.0) > 0.0],
            key=lambda x: values[x],
            reverse=True
        )
        opp_vals = [values[o] for o in sorted_opponents]
        avg = round(sum(opp_vals)/len(opp_vals), 3) if opp_vals else 0.0
        # Format opponents for HTML display
        opp_info_str = "<br>".join([f"{o} ({values[o]} M€)" for o in sorted_opponents])
        rows.append((team, avg, opp_info_str))
    return sorted(rows, key=lambda x: x[1], reverse=True)

# -------------------- HTML Export --------------------
def export_to_html(data, competition_name):
    filename = competition_name.lower().replace(" ", "_") + "_opponents.html"
    df = pd.DataFrame(data, columns=["Team", "Avg Opponent Market Value (M€)", "Opponents (M€)"])
    html_content = f"""
    <html>
    <head>
        <title>{competition_name} Opponent Market Values</title>
        <style>
            table {{
                border-collapse: collapse;
                width: 100%;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #4CAF50;
                color: white;
            }}
            tr:nth-child(even){{background-color: #f2f2f2;}}
            tr:hover {{background-color: #ddd;}}
        </style>
    </head>
    <body>
        <h2>{competition_name} Average Opponent Market Values</h2>
        {df.to_html(index=False, escape=False)}
    </body>
    </html>
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\nHTML file created: {filename}")

# -------------------- Main Workflow --------------------
def main():
    comp_code, comp_name = select_competition()

    tm_teams_url = f"https://www.transfermarkt.com/uefa-{comp_name.lower().replace(' ','-')}/teilnehmer/pokalwettbewerb/{comp_code}"
    tm_fixtures_url = f"https://www.transfermarkt.com/uefa-{comp_name.lower().replace(' ','-')}/gesamtspielplan/pokalwettbewerb/{comp_code}/saison_id/2025"

    print(f"\nScraping {comp_name} team values...")
    tm_values = scrape_tm_team_values(tm_teams_url)

    print(f"Scraping {comp_name} fixtures...")
    opp_map = scrape_tm_fixtures(tm_fixtures_url)

    print("Calculating average opponent values and sorting opponents...")
    avg_opponent_info = calculate_opponent_info(opp_map, tm_values)

    # Export to HTML
    export_to_html(avg_opponent_info, comp_name)

if __name__ == "__main__":
    main()
