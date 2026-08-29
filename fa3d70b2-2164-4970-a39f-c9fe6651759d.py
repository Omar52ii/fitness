
import sqlite3
from datetime import date, datetime, timedelta
from io import BytesIO

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB = "fitness_data.db"

st.set_page_config(
    page_title="Tactical Fitness Tracker",
    page_icon="🎖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Database ----------
def conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    c = conn()
    cur = c.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        muscle_group TEXT NOT NULL,
        exercise TEXT NOT NULL,
        sets INTEGER NOT NULL,
        reps INTEGER NOT NULL,
        weight_kg REAL NOT NULL,
        rpe REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS cardio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        activity TEXT NOT NULL,
        duration_min REAL NOT NULL,
        distance_km REAL NOT NULL,
        avg_hr INTEGER,
        notes TEXT,
        pace_min_km REAL
    );

    CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        pullups REAL,
        pushups_2min REAL,
        situps_2min REAL,
        run_1500_sec REAL,
        swim_min REAL,
        water_tread_min REAL,
        readiness_score REAL
    );

    CREATE TABLE IF NOT EXISTS meals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        meal_type TEXT NOT NULL,
        calories REAL NOT NULL,
        protein_g REAL NOT NULL,
        carbs_g REAL NOT NULL,
        fats_g REAL NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS body (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        weight_kg REAL NOT NULL,
        body_fat REAL,
        chest_cm REAL,
        arm_cm REAL,
        waist_cm REAL
    );
    """)
    defaults = {
        "calorie_target": "3000",
        "protein_target": "150",
        "weight_target": "80",
    }
    for k, v in defaults.items():
        cur.execute("INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)", (k, v))
    c.commit()
    c.close()

def read_df(table):
    c = conn()
    df = pd.read_sql_query(f"SELECT * FROM {table}", c)
    c.close()
    return df

def execute(sql, params=()):
    c = conn()
    c.execute(sql, params)
    c.commit()
    c.close()

def setting(key):
    c = conn()
    row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    c.close()
    return float(row[0]) if row else 0

def set_setting(key, value):
    execute("INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)", (key, str(value)))

init_db()

# ---------- Styling ----------
st.markdown("""
<style>
:root { --accent:#8fa83d; }
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at top right, #182019 0, #0d110f 38%, #080a09 100%);
}
[data-testid="stSidebar"] {
    background: #0b0f0c;
    border-right: 1px solid #293329;
}
.block-container { max-width: 1450px; padding-top: 1.2rem; }
h1,h2,h3 { letter-spacing: .3px; }
div[data-testid="stMetric"] {
    background: #111711;
    border: 1px solid #293329;
    border-radius: 12px;
    padding: 12px;
}
.stProgress > div > div > div > div { background: #8fa83d; }
div.stButton > button, div.stDownloadButton > button {
    border-radius: 9px;
    border: 1px solid #45563d;
}
.small-muted { color:#9ca79b; font-size:.86rem; }
.badge {
    display:inline-block; padding:5px 10px; border-radius:20px;
    background:#20291d; border:1px solid #45563d; color:#c4d49c;
}
</style>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
def pct(value, target):
    return min(max(value / target, 0), 1) if target else 0

def pace(duration, distance):
    return duration / distance if distance and distance > 0 else None

def format_pace(x):
    if x is None or pd.isna(x): return "—"
    m = int(x)
    s = round((x - m) * 60)
    if s == 60: m, s = m + 1, 0
    return f"{m}:{s:02d}/km"

def score_readiness(pullups, pushups, situps, run_sec, swim, tread):
    # Transparent normalized benchmark model; not an official military standard.
    parts = [
        min(max((pullups / 15) * 100, 0), 100),
        min(max((pushups / 60) * 100, 0), 100),
        min(max((situps / 60) * 100, 0), 100),
        min(max((900 / run_sec) * 100, 0), 100) if run_sec else 0,
        min(max((swim / 20) * 100, 0), 100),
        min(max((tread / 10) * 100, 0), 100),
    ]
    return round(sum(parts) / len(parts), 1)

def to_excel():
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for table in ["workouts","cardio","tests","meals","body"]:
            read_df(table).to_excel(writer, index=False, sheet_name=table)
    output.seek(0)
    return output

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🎖️ TACTICAL")
    st.markdown("**Fitness & Readiness Tracker**")
    st.markdown('<span class="badge">LOCAL • SQLITE</span>', unsafe_allow_html=True)
    st.divider()
    page = st.radio(
        "Navigation / التنقل",
        ["🏠 Dashboard", "🏋️ Workouts", "🏃 Cardio", "🎯 Readiness Tests",
         "🥗 Nutrition", "📏 Body Composition", "🗄️ Data & Export", "⚙️ Settings"]
    )
    st.divider()
    st.caption("Progressive overload • Endurance • Readiness • Clean bulk")
    st.caption("⚠️ Readiness benchmarks are illustrative, not official standards.")

# ---------- Dashboard ----------
if page == "🏠 Dashboard":
    st.title("🎖️ Tactical Fitness Dashboard")
    st.caption("Daily command center / مركز المتابعة اليومية")

    today = date.today().isoformat()
    meals = read_df("meals")
    cardio = read_df("cardio")
    workouts = read_df("workouts")
    body = read_df("body")

    today_meals = meals[meals.date == today] if not meals.empty else meals
    kcal = today_meals.calories.sum() if not today_meals.empty else 0
    protein = today_meals.protein_g.sum() if not today_meals.empty else 0

    calorie_target = setting("calorie_target")
    protein_target = setting("protein_target")
    current_weight = body.sort_values("date").iloc[-1].weight_kg if not body.empty else 0

    week_start = (date.today() - timedelta(days=6)).isoformat()
    week_cardio = cardio[cardio.date >= week_start] if not cardio.empty else cardio
    week_workouts = workouts[workouts.date >= week_start] if not workouts.empty else workouts
    run_km = week_cardio.distance_km.sum() if not week_cardio.empty else 0

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🔥 Calories Today", f"{kcal:.0f} kcal", f"Target {calorie_target:.0f}")
    c2.metric("🥩 Protein Today", f"{protein:.0f} g", f"Target {protein_target:.0f} g")
    c3.metric("🏋️ Workouts / 7d", len(week_workouts))
    c4.metric("🏃 Distance / 7d", f"{run_km:.1f} km", f"Weight {current_weight:.1f} kg" if current_weight else "No weight logged")

    st.subheader("Daily Targets / أهداف اليوم")
    p1,p2 = st.columns(2)
    with p1:
        st.write(f"Calories — **{kcal:.0f} / {calorie_target:.0f} kcal**")
        st.progress(pct(kcal, calorie_target))
    with p2:
        st.write(f"Protein — **{protein:.0f} / {protein_target:.0f} g**")
        st.progress(pct(protein, protein_target))

    st.subheader("Latest Body & Training Snapshot")
    a,b = st.columns(2)
    with a:
        if not body.empty:
            bdf = body.copy()
            bdf["date"] = pd.to_datetime(bdf["date"])
            bdf = bdf.sort_values("date")
            bdf["MA 7d"] = bdf.weight_kg.rolling(7, min_periods=1).mean()
            fig = px.line(bdf, x="date", y=["weight_kg","MA 7d"], markers=True,
                          title="Body Weight / الوزن")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Log your first body measurement.")
    with b:
        if not cardio.empty:
            cdf = cardio.copy()
            cdf["date"] = pd.to_datetime(cdf["date"])
            daily = cdf.groupby("date", as_index=False).distance_km.sum()
            fig = px.bar(daily, x="date", y="distance_km", title="Running / Cardio Distance")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Log a cardio session to see trends.")

# ---------- Workouts ----------
elif page == "🏋️ Workouts":
    st.title("🏋️ Gym Workouts Logger")
    st.caption("Upper / Lower / Push-Pull-Legs • Progressive Overload")

    with st.form("workout_form", clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        d = c1.date_input("Date / التاريخ", value=date.today())
        muscle = c2.selectbox("Muscle Group / العضلة", ["Chest","Back","Shoulders","Arms","Legs","Calisthenics/Core"])
        exercise = c3.text_input("Exercise / التمرين", placeholder="Bench Press")
        c4,c5,c6,c7 = st.columns(4)
        sets = c4.number_input("Sets", 1, 30, 3)
        reps = c5.number_input("Reps", 1, 100, 8)
        weight = c6.number_input("Weight (kg)", 0.0, 500.0, 20.0, step=0.5)
        rpe = c7.number_input("RPE", 1.0, 10.0, 7.0, step=0.5)
        if st.form_submit_button("➕ Log Workout"):
            if exercise.strip():
                execute("""INSERT INTO workouts(date,muscle_group,exercise,sets,reps,weight_kg,rpe)
                           VALUES (?,?,?,?,?,?,?)""",
                        (d.isoformat(), muscle, exercise.strip(), sets, reps, weight, rpe))
                st.success("Workout logged.")
                st.rerun()

    df = read_df("workouts")
    if not df.empty:
        st.subheader("Progressive Overload Analytics")
        exercises = sorted(df.exercise.unique())
        selected = st.selectbox("Exercise / اختر التمرين", exercises)
        x = df[df.exercise == selected].copy()
        x["date"] = pd.to_datetime(x["date"])
        x["volume"] = x.sets * x.reps * x.weight_kg
        x = x.sort_values("date")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x.date, y=x.weight_kg, mode="lines+markers", name="Weight kg"))
        fig.add_trace(go.Scatter(x=x.date, y=x.volume, mode="lines+markers", name="Volume kg"))
        fig.update_layout(title=f"{selected} — Weight & Volume", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df.sort_values("date", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("No workouts logged yet.")

# ---------- Cardio ----------
elif page == "🏃 Cardio":
    st.title("🏃 Tactical Cardio & Endurance")
    with st.form("cardio_form", clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        d = c1.date_input("Date / التاريخ", value=date.today())
        activity = c2.selectbox("Activity / النشاط",
            ["1500m Time Trial","Interval Sprints","Long Distance Run","Swimming","Ruck Marching"])
        duration = c3.number_input("Duration (min)", 0.1, 1000.0, 20.0)
        c4,c5,c6 = st.columns(3)
        distance = c4.number_input("Distance (km)", 0.0, 500.0, 1.5, step=0.1)
        hr = c5.number_input("Avg HR (bpm)", 0, 250, 0)
        notes = c6.text_input("Tactical Notes")
        calculated = pace(duration, distance)
        st.info(f"Automatic pace / السرعة: **{format_pace(calculated)}**")
        if st.form_submit_button("➕ Log Cardio"):
            execute("""INSERT INTO cardio(date,activity,duration_min,distance_km,avg_hr,notes,pace_min_km)
                       VALUES (?,?,?,?,?,?,?)""",
                    (d.isoformat(), activity, duration, distance, int(hr) if hr else None, notes, calculated))
            st.success("Cardio session logged.")
            st.rerun()

    df = read_df("cardio")
    if not df.empty:
        c1,c2 = st.columns(2)
        with c1:
            r = df[df.activity=="1500m Time Trial"].copy()
            if not r.empty:
                r["date"] = pd.to_datetime(r.date)
                fig = px.line(r.sort_values("date"), x="date", y="duration_min", markers=True,
                              title="1500m Time Trend — lower is better")
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            df["date"] = pd.to_datetime(df.date)
            weekly = df.set_index("date").resample("W").distance_km.sum().reset_index()
            fig = px.line(weekly, x="date", y="distance_km", markers=True, title="Weekly Mileage")
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df.sort_values("date", ascending=False), use_container_width=True, hide_index=True)

# ---------- Readiness ----------
elif page == "🎯 Readiness Tests":
    st.title("🎯 Military Readiness & Tactical Fitness")
    st.caption("Illustrative scoring engine — not an official Special Forces assessment.")

    with st.form("test_form", clear_on_submit=True):
        d = st.date_input("Date / التاريخ", value=date.today())
        c1,c2,c3 = st.columns(3)
        pull = c1.number_input("Pull-ups / العقلة", 0.0, 100.0, 10.0)
        push = c2.number_input("Push-ups 2 min", 0.0, 200.0, 40.0)
        sit = c3.number_input("Sit-ups 2 min", 0.0, 200.0, 40.0)
        c4,c5,c6 = st.columns(3)
        run = c4.number_input("1500m Time (sec)", 1.0, 3600.0, 420.0)
        swim = c5.number_input("Swimming (min)", 0.0, 180.0, 10.0)
        tread = c6.number_input("Water Treading (min)", 0.0, 180.0, 5.0)
        score = score_readiness(pull,push,sit,run,swim,tread)
        st.metric("Readiness Score", f"{score:.1f}%")
        if st.form_submit_button("💾 Save Test"):
            execute("""INSERT INTO tests(date,pullups,pushups_2min,situps_2min,run_1500_sec,swim_min,water_tread_min,readiness_score)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (d.isoformat(),pull,push,sit,run,swim,tread,score))
            st.success("Assessment saved.")
            st.rerun()

    df = read_df("tests")
    if not df.empty:
        df["date"] = pd.to_datetime(df.date)
        fig = px.line(df.sort_values("date"), x="date", y="readiness_score", markers=True,
                      range_y=[0,100], title="Readiness Score Trend")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df.sort_values("date", ascending=False), use_container_width=True, hide_index=True)

# ---------- Nutrition ----------
elif page == "🥗 Nutrition":
    st.title("🥗 Nutrition & Macro Tracker")
    st.caption("Clean Bulk • السعرات والماكروز")

    with st.form("meal_form", clear_on_submit=True):
        c1,c2 = st.columns(2)
        d = c1.date_input("Date / التاريخ", value=date.today())
        meal = c2.selectbox("Meal Type / الوجبة", ["Breakfast","Lunch","Post-workout Shake","Dinner","Snacks"])
        c3,c4,c5,c6 = st.columns(4)
        kcal = c3.number_input("Calories", 0.0, 10000.0, 500.0)
        protein = c4.number_input("Protein (g)", 0.0, 500.0, 30.0)
        carbs = c5.number_input("Carbs (g)", 0.0, 1000.0, 50.0)
        fats = c6.number_input("Fats (g)", 0.0, 500.0, 15.0)
        desc = st.text_input("Description / الوصف")
        quick = st.text_input("Fast Add (optional) / إضافة سريعة", placeholder="4 eggs, 2 bread, 150g oats")
        if st.form_submit_button("➕ Log Meal"):
            final_desc = desc
            if quick.strip():
                final_desc = (desc + " | " if desc else "") + "Fast Add: " + quick.strip()
            execute("""INSERT INTO meals(date,meal_type,calories,protein_g,carbs_g,fats_g,description)
                       VALUES (?,?,?,?,?,?,?)""",
                    (d.isoformat(),meal,kcal,protein,carbs,fats,final_desc))
            st.success("Meal logged.")
            st.rerun()

    df = read_df("meals")
    if not df.empty:
        target_date = st.date_input("Summary date / يوم الملخص", value=date.today(), key="nutrition_date")
        day = df[df.date == target_date.isoformat()]
        totals = day[["calories","protein_g","carbs_g","fats_g"]].sum() if not day.empty else pd.Series([0,0,0,0], index=["calories","protein_g","carbs_g","fats_g"])
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Calories", f"{totals.calories:.0f} kcal")
        c2.metric("Protein", f"{totals.protein_g:.0f} g")
        c3.metric("Carbs", f"{totals.carbs_g:.0f} g")
        c4.metric("Fats", f"{totals.fats_g:.0f} g")

        p = pd.DataFrame({"Macro":["Protein","Carbs","Fats"],
                          "Grams":[totals.protein_g,totals.carbs_g,totals.fats_g]})
        fig = px.pie(p, names="Macro", values="Grams", hole=.35, title="Macro Distribution")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(day.sort_values("id", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("No meals logged yet.")

# ---------- Body ----------
elif page == "📏 Body Composition":
    st.title("📏 Body Composition & Transformation")
    st.caption("Weight • Body Fat • Circumference")

    with st.form("body_form", clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        d = c1.date_input("Date / التاريخ", value=date.today())
        weight = c2.number_input("Body Weight (kg)", 1.0, 300.0, 70.0)
        bf = c3.number_input("Body Fat %", 0.0, 80.0, 15.0)
        c4,c5,c6 = st.columns(3)
        chest = c4.number_input("Chest (cm)", 0.0, 200.0, 90.0)
        arm = c5.number_input("Arm (cm)", 0.0, 100.0, 30.0)
        waist = c6.number_input("Waist (cm)", 0.0, 200.0, 80.0)
        if st.form_submit_button("➕ Save Measurement"):
            execute("""INSERT INTO body(date,weight_kg,body_fat,chest_cm,arm_cm,waist_cm)
                       VALUES (?,?,?,?,?,?)""",
                    (d.isoformat(),weight,bf,chest,arm,waist))
            st.success("Measurement saved.")
            st.rerun()

    df = read_df("body")
    if not df.empty:
        df["date"] = pd.to_datetime(df.date)
        df = df.sort_values("date")
        df["7d moving avg"] = df.weight_kg.rolling(7, min_periods=1).mean()
        fig = px.line(df, x="date", y=["weight_kg","7d moving avg"], markers=True,
                      title="Weight Progression & Moving Average")
        st.plotly_chart(fig, use_container_width=True)
        st.info("Clean-bulk reference: roughly 1–1.5 kg/month. Individual targets vary; use this as a tracking reference, not a medical recommendation.")
        st.dataframe(df.sort_values("date", ascending=False), use_container_width=True, hide_index=True)

# ---------- Data ----------
elif page == "🗄️ Data & Export":
    st.title("🗄️ Data Management & Export")
    st.caption("Live SQL viewer • Search • CSV • Excel • SQLite backup")

    tables = ["workouts","cardio","tests","meals","body"]
    table = st.selectbox("Table / الجدول", tables)
    df = read_df(table)
    search = st.text_input("Search / بحث")
    if search and not df.empty:
        mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False))
        df = df[mask.any(axis=1)]
    st.dataframe(df, use_container_width=True, hide_index=True)

    c1,c2,c3 = st.columns(3)
    with c1:
        st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode("utf-8"), f"{table}.csv", "text/csv")
    with c2:
        st.download_button("⬇️ Download Excel", to_excel(), "fitness_data.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with c3:
        with open(DB, "rb") as f:
            st.download_button("💾 SQLite Backup", f, "fitness_data.db", "application/x-sqlite3")

    st.divider()
    st.subheader("Database Summary")
    for t in tables:
        st.write(f"**{t}** — {len(read_df(t))} records")

# ---------- Settings ----------
else:
    st.title("⚙️ Settings / الإعدادات")
    st.caption("Customize your daily targets")
    c1,c2,c3 = st.columns(3)
    cal = c1.number_input("Daily Calories", 500.0, 10000.0, setting("calorie_target"), step=50.0)
    prot = c2.number_input("Daily Protein (g)", 20.0, 500.0, setting("protein_target"), step=5.0)
    wt = c3.number_input("Target Weight (kg)", 20.0, 250.0, setting("weight_target"), step=0.5)
    if st.button("💾 Save Settings"):
        set_setting("calorie_target", cal)
        set_setting("protein_target", prot)
        set_setting("weight_target", wt)
        st.success("Settings saved.")
        st.rerun()

    st.divider()
    st.subheader("Readiness Scoring Model")
    st.write("""
    The readiness engine currently uses six normalized components: pull-ups, 2-minute push-ups,
    2-minute sit-ups, 1500m run time, swimming duration, and water-treading duration.
    It is intentionally transparent and configurable rather than claiming to reproduce an official
    military or Special Forces standard.
    """)
