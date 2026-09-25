"""
Settings for the PvA agent team. Change things here, not inside the agents.
"""
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
DB_PATH = HERE / "data" / "footwear.db"      # synthetic warehouse (built by data.py)
OUT_DIR = HERE / "out"                        # drafts + approved reports land here

# ---- "Now" in the simulation ------------------------------------------------
MONTH_START = date(2026, 9, 1)
MONTH_END = date(2026, 9, 30)
AS_OF_DATE = date(2026, 9, 25)   # today
AS_OF_HOUR = 15                  # intraday data is loaded up to 14:59

# ---- When is PvA "low"? -----------------------------------------------------
# Volume metrics (sessions, list views, PDP views, ATC, orders, units, GMV, GM)
VOLUME_THRESHOLD = {"mtd": 0.95, "intraday": 0.90}
# Ratio metrics (LV/session, PDP CTR, consideration, checkout, conversion, UPT, ASP)
# move less than volumes, so a smaller miss is already meaningful.
RATE_THRESHOLD = {"mtd": 0.97, "intraday": 0.95}

# ---- Levers the action agents may propose ----------------------------------------
REBATE_TOPUP_INR = 5_000_000      # extra MP rebate the category head could release (INR 50 lakh)

# ---- Your team (MADE-UP names for the demo -- edit to match your real team) ------
# free hours this week = capacity_hrs - committed_hrs (BAU reporting, meetings)
TEAM = [
    {"name": "Asha", "role": "Senior Analyst", "skills": ["planning", "reporting", "pricing", "rebates"],
     "capacity_hrs": 30, "committed_hrs": 14, "growth_goal": "run the monthly leadership review end to end"},
    {"name": "Rohan", "role": "Analyst", "skills": ["funnel", "traffic", "sql", "experiments"],
     "capacity_hrs": 35, "committed_hrs": 20, "growth_goal": "move from reporting numbers to recommending actions"},
    {"name": "Meera", "role": "Analyst", "skills": ["supply", "merchandising", "sql"],
     "capacity_hrs": 35, "committed_hrs": 12, "growth_goal": "influence buyers and planners with data"},
    {"name": "Kabir", "role": "Associate Analyst", "skills": ["dashboards", "sql", "brand packs"],
     "capacity_hrs": 40, "committed_hrs": 26, "growth_goal": "lead a brand-partner review meeting"},
]

# ---- LLM settings ------------------------------------------------------------
MODEL = "claude-opus-5"
MAX_TOKENS = 16000
MAX_AGENT_TURNS = 20        # safety stop for any one agent's tool loop
MAX_REVIEW_ROUNDS = 2       # Writer <-> Reviewer back-and-forth before handing to you
