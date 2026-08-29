import io
import os
import re
import requests
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="Tactical Fitness Tracker", page_icon="🎖️", layout="wide", initial_sidebar_state="expanded")

# ------------------------- Exercise Library -------------------------
EXERCISES = {
    "Chest": ["Barbell Bench Press", "Incline Barbell Bench Press", "Decline Barbell Bench Press", "Dumbbell Bench Press", "Incline Dumbbell Press", "Decline Dumbbell Press", "Machine Chest Press", "Smith Machine Bench Press", "Cable Chest Press", "Cable Crossover", "Low-to-High Cable Fly", "High-to-Low Cable Fly", "Pec Deck Fly", "Dumbbell Fly", "Incline Dumbbell Fly", "Push-Ups", "Weighted Push-Ups", "Chest Dips", "Landmine Press", "Svend Press"],
    "Back": ["Pull-Ups", "Weighted Pull-Ups", "Chin-Ups", "Lat Pulldown", "Close-Grip Lat Pulldown", "Wide-Grip Lat Pulldown", "Neutral-Grip Pulldown", "Barbell Row", "Pendlay Row", "T-Bar Row", "Chest-Supported Row", "Seated Cable Row", "One-Arm Dumbbell Row", "Machine Row", "Straight-Arm Pulldown", "Face Pull", "Dumbbell Pullover"],
    "Shoulders": ["Barbell Overhead Press", "Dumbbell Shoulder Press", "Arnold Press", "Machine Shoulder Press", "Seated Dumbbell Press", "Dumbbell Lateral Raise", "Cable Lateral Raise", "Machine Lateral Raise", "Front Raise", "Cable Front Raise", "Rear Delt Fly", "Reverse Pec Deck", "Upright Row", "Face Pull"],
    "Arms": ["Barbell Curl", "EZ-Bar Curl", "Dumbbell Curl", "Hammer Curl", "Incline Dumbbell Curl", "Preacher Curl", "Spider Curl", "Concentration Curl", "Cable Curl", "Bayesian Cable Curl", "Reverse Curl", "Cable Triceps Pushdown", "Rope Pushdown", "Straight-Bar Pushdown", "Overhead Cable Extension", "Dumbbell Overhead Extension", "Skull Crushers", "Close-Grip Bench Press", "Triceps Dips", "Triceps Kickback", "Machine Triceps Extension"],
    "Legs": ["Back Squat", "Front Squat", "Hack Squat", "Leg Press", "Bulgarian Split Squat", "Walking Lunges", "Reverse Lunges", "Romanian Deadlift", "Stiff-Leg Deadlift", "Leg Extension", "Lying Leg Curl", "Seated Leg Curl", "Nordic Curl", "Hip Thrust", "Glute Bridge", "Cable Kickback", "Standing Calf Raise", "Seated Calf Raise"],
    "Calisthenics/Core": ["Push-Ups", "Pull-Ups", "Chin-Ups", "Dips", "Muscle-Up", "Handstand Push-Up", "Plank", "Side Plank", "Hanging Leg Raise", "Hanging Knee Raise", "Toes-to-Bar", "Ab Wheel", "Cable Crunch", "Russian Twist", "Bicycle Crunch", "Sit-Ups", "V-Ups"],
}

DEMO_SEARCH = {
    "Pull-Ups":"pull up exercise form", "Chin-Ups":"chin up exercise form", "Lat Pulldown":"lat pulldown exercise form",
    "Barbell Bench Press":"barbell bench press exercise form", "Incline Barbell Bench Press":"incline bench press exercise form",
    "Dumbbell Bench Press":"dumbbell bench press exercise form", "Incline Dumbbell Press":"incline dumbbell press exercise form",
    "Back Squat":"barbell back squat exercise form", "Romanian Deadlift":"romanian deadlift exercise form",
    "Barbell Curl":"barbell biceps curl exercise form", "Hammer Curl":"hammer curl exercise form",
    "Cable Triceps Pushdown":"triceps pushdown exercise form", "Dumbbell Lateral Raise":"dumbbell lateral raise exercise form",
}

# ------------------------- Styling -------------------------
st.markdown("""
<style>
:root{--accent:#8fa83d;--panel:#111711;--border:#2c382d;--muted:#9ca79b}
[data-testid="stAppViewContainer"]{background:radial-gradient(circle at top right,#182019 0,#0d110f 38%,#080a09 100%)}
[data-testid="stSidebar"]{background:#0b0f0c;border-right:1px solid var(--border)}
.block-container{max-width:1450px;padding-top:1.1rem}
h1,h2,h3{letter-spacing:.2px}
div[data-testid="stMetric"]{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:12px}
.small-muted{color:var(--muted);font-size:.86rem}.badge{display:inline-block;padding:5px 10px;border-radius:20px;background:#20291d;border:1px solid #45563d;color:#c4d49c}
.exercise-card{padding:16px;border:1px solid var(--border);border-radius:14px;background:rgba(17,23,17,.8);margin:8px 0}
</style>""", unsafe_allow_html=True)

# ------------------------- Supabase -------------------------
def get_client() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception as e:
        st.error("Supabase secrets are missing. Add SUPABASE_URL and SUPABASE_KEY in Streamlit Secrets.")
        st.stop()
    return create_client(url, key)

if "sb" not in st.session_state:
    st.session_state.sb = get_client()
sb = st.session_state.sb

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,24}$")
AUTH_DOMAIN = "users.tacticalfitness.local"

def normalize_username(u): return u.strip().lower()
def auth_email(u): return f"{normalize_username(u)}@{AUTH_DOMAIN}"

def auth_error_message(e):
    msg = str(e)
    low = msg.lower()
    if "already registered" in low or "already been registered" in low or "user already exists" in low:
        return "اسم المستخدم ده مستخدم بالفعل. اختار Username مختلف."
    if "password" in low and ("weak" in low or "least" in low or "characters" in low):
        return "الباسورد ضعيف. استخدم 8 أحرف على الأقل مع حروف وأرقام ورمز."
    if "invalid login credentials" in low:
        return "اسم المستخدم أو الباسورد غير صحيح."
    if "email not confirmed" in low:
        return "الحساب يحتاج تأكيد البريد. من إعدادات Supabase اقفل Confirm email."
    return msg

def sign_out():
    try: sb.auth.sign_out()
    except Exception: pass
    st.session_state.pop("user", None)
    st.rerun()

def login_screen():
    st.markdown("# 🎖️ Tactical Fitness Tracker")
    st.caption("Your private training command center")
    left, center, right = st.columns([1, 1.4, 1])
    with center:
        tab_login, tab_signup = st.tabs(["🔐 Login", "➕ Create Account"])
        with tab_login:
            with st.form("login"):
                username = st.text_input("Username", placeholder="omar")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted:
                u = normalize_username(username)
                if not USERNAME_RE.fullmatch(u):
                    st.error("Username: 3–24 characters, lowercase letters, numbers, or underscore only.")
                elif not password:
                    st.error("اكتب الباسورد.")
                else:
                    try:
                        res = sb.auth.sign_in_with_password({"email": auth_email(u), "password": password})
                        if res.user:
                            st.session_state.user = res.user
                            st.rerun()
                    except Exception as e:
                        st.error(auth_error_message(e))
        with tab_signup:
            with st.form("signup"):
                name = st.text_input("Display Name", placeholder="Omar")
                username = st.text_input("Username", placeholder="omar")
                password = st.text_input("Password", type="password")
                confirm = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button("Create Account", use_container_width=True)
            if submitted:
                u = normalize_username(username)
                if not USERNAME_RE.fullmatch(u):
                    st.error("Username: 3–24 characters, lowercase letters, numbers, or underscore only.")
                elif len(password) < 8:
                    st.error("الباسورد لازم يكون 8 أحرف على الأقل.")
                elif password != confirm:
                    st.error("الباسوردين مش متطابقين.")
                else:
                    try:
                        res = sb.auth.sign_up({"email": auth_email(u), "password": password, "options": {"data": {"display_name": name.strip() or u, "username": u}}})
                        if res.user and res.session:
                            st.session_state.user = res.user
                            st.success("Account created.")
                            st.rerun()
                        elif res.user:
                            st.warning("الحساب اتعمل، لكن Supabase طالب Email Confirmation. اقفل Confirm email من Authentication → Providers → Email.")
                        else:
                            st.error("لم يتم إنشاء الحساب.")
                    except Exception as e:
                        st.error(auth_error_message(e))

if "user" not in st.session_state:
    try:
        current = sb.auth.get_user()
        if current and current.user: st.session_state.user = current.user
    except Exception: pass

if "user" not in st.session_state:
    login_screen(); st.stop()

USER_ID = st.session_state.user.id

# ------------------------- Data helpers -------------------------
TABLES = ["workouts","cardio","tests","meals","body"]

def select_df(table, order_col="date"):
    q = sb.table(table).select("*").eq("user_id", USER_ID)
    if order_col: q = q.order(order_col, desc=True)
    res = q.execute()
    return pd.DataFrame(res.data or [])

def insert(table, payload):
    payload = dict(payload); payload["user_id"] = USER_ID
    return sb.table(table).insert(payload).execute()

def get_settings():
    res = sb.table("settings").select("key,value").eq("user_id", USER_ID).execute()
    return {r["key"]: float(r["value"]) for r in (res.data or [])}

def save_settings(values):
    for k,v in values.items():
        sb.table("settings").upsert({"user_id":USER_ID,"key":k,"value":str(v)}, on_conflict="user_id,key").execute()

def pct(v,t): return min(max(v/t,0),1) if t else 0
def pace(duration,distance): return duration/distance if distance and distance>0 else None
def format_pace(x):
    if x is None or pd.isna(x): return "—"
    m=int(x); s=round((x-m)*60)
    if s==60: m+=1; s=0
    return f"{m}:{s:02d}/km"
def score_readiness(pullups,pushups,situps,run_sec,swim,tread):
    parts=[min(max(pullups/15*100,0),100),min(max(pushups/60*100,0),100),min(max(situps/60*100,0),100),min(max(900/run_sec*100,0),100) if run_sec else 0,min(max(swim/20*100,0),100),min(max(tread/10*100,0),100)]
    return round(sum(parts)/len(parts),1)
def to_excel(dfs):
    out=io.BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as w:
        for name,df in dfs.items(): df.to_excel(w,index=False,sheet_name=name)
    out.seek(0); return out

def exercise_demo_url(exercise):
    q=DEMO_SEARCH.get(exercise, f"{exercise} exercise form")
    return "https://www.google.com/search?tbm=isch&q=" + q.replace(" ","+")

def exercise_image(exercise):
    """Try Wger's public exercise image API; no image is stored in the app."""
    try:
        r=requests.get("https://wger.de/api/v2/exercise/search/",params={"term":exercise,"language":2,"format":"json"},timeout=3)
        r.raise_for_status()
        results=r.json().get("suggestions",[])
        if results and results[0].get("image_url"):
            return results[0]["image_url"]
    except Exception:
        pass
    return None

settings=get_settings()
calorie_target=settings.get("calorie_target",3000)
protein_target=settings.get("protein_target",150)
weight_target=settings.get("weight_target",80)

# ------------------------- Sidebar -------------------------
with st.sidebar:
    st.markdown("## 🎖️ TACTICAL")
    st.markdown("**Fitness & Readiness Tracker**")
    st.markdown('<span class="badge">SECURE • PERSONAL</span>',unsafe_allow_html=True)
    st.caption(f"👤 {st.session_state.user.user_metadata.get('display_name') or st.session_state.user.user_metadata.get('username') or 'User'}")
    if st.button("🚪 Logout",use_container_width=True): sign_out()
    st.divider()
    page=st.radio("Navigation / التنقل",["🏠 Dashboard","🏋️ Workouts","🏃 Cardio","🎯 Readiness Tests","🥗 Nutrition","📏 Body Composition","🗄️ Data & Export","⚙️ Settings"])
    st.divider(); st.caption("Progressive overload • Endurance • Readiness")

# ------------------------- Dashboard -------------------------
if page=="🏠 Dashboard":
    st.title("🎖️ Tactical Fitness Dashboard")
    st.caption("Daily command center / مركز المتابعة اليومية")
    today=date.today().isoformat()
    meals=select_df("meals"); cardio=select_df("cardio"); workouts=select_df("workouts"); body=select_df("body"); tests=select_df("tests")
    tm=meals[meals.date==today] if not meals.empty else meals
    kcal=tm.calories.sum() if not tm.empty else 0; protein=tm.protein_g.sum() if not tm.empty else 0
    weight=float(body.iloc[0].weight_kg) if not body.empty else 0
    ws=(date.today()-timedelta(days=6)).isoformat()
    wc=cardio[cardio.date>=ws] if not cardio.empty else cardio; ww=workouts[workouts.date>=ws] if not workouts.empty else workouts
    c1,c2,c3,c4=st.columns(4); c1.metric("🔥 Calories Today",f"{kcal:.0f}",f"Target {calorie_target:.0f}"); c2.metric("🥩 Protein Today",f"{protein:.0f} g",f"Target {protein_target:.0f} g"); c3.metric("🏋️ Workouts / 7d",len(ww)); c4.metric("🏃 Distance / 7d",f"{wc.distance_km.sum():.1f} km" if not wc.empty else "0 km",f"Weight {weight:.1f} kg" if weight else "No weight logged")
    a,b=st.columns(2)
    with a:
        st.subheader("Daily Targets"); st.write(f"Calories — **{kcal:.0f} / {calorie_target:.0f} kcal**"); st.progress(pct(kcal,calorie_target)); st.write(f"Protein — **{protein:.0f} / {protein_target:.0f} g**"); st.progress(pct(protein,protein_target))
    with b:
        st.subheader("🏆 Latest PR / Readiness")
        if not tests.empty: st.metric("Latest Readiness",f"{tests.iloc[0].readiness_score:.1f}%")
        else: st.info("Save your first readiness test.")
    st.subheader("Progress")
    a,b=st.columns(2)
    with a:
        if not body.empty:
            x=body.copy(); x.date=pd.to_datetime(x.date); x=x.sort_values("date"); x["7d MA"]=x.weight_kg.rolling(7,min_periods=1).mean(); fig=px.line(x,x="date",y=["weight_kg","7d MA"],markers=True,title="Body Weight"); st.plotly_chart(fig,use_container_width=True)
        else: st.info("Log a body measurement to see progress.")
    with b:
        if not workouts.empty:
            v=workouts.copy(); v["date"]=pd.to_datetime(v.date); v["volume"]=v.sets*v.reps*v.weight_kg; daily=v.groupby("date",as_index=False).volume.sum(); fig=px.bar(daily,x="date",y="volume",title="Training Volume"); st.plotly_chart(fig,use_container_width=True)
        else: st.info("Log a workout to see training volume.")

# ------------------------- Workouts -------------------------
elif page=="🏋️ Workouts":
    st.title("🏋️ Gym Workouts")
    muscle=st.selectbox("Muscle Group / العضلة",list(EXERCISES.keys()))
    options=EXERCISES[muscle]+["✏️ Custom Exercise"]
    exercise_choice=st.selectbox("Exercise / التمرين",options)
    if exercise_choice=="✏️ Custom Exercise": exercise=st.text_input("Custom Exercise Name")
    else: exercise=exercise_choice
    if exercise:
        img=exercise_image(exercise) if exercise_choice!="✏️ Custom Exercise" else None
        if img:
            st.image(img,caption=f"{exercise} — demo",width=420)
        else:
            st.markdown(f'<div class="exercise-card"><b>🎥 Exercise Demo</b><br><span class="small-muted">{exercise}</span><br><a href="{exercise_demo_url(exercise)}" target="_blank">Open demo images / افتح صور توضيحية ↗</a></div>',unsafe_allow_html=True)
    hist=select_df("workouts")
    if exercise and not hist.empty:
        hx=hist[hist.exercise.str.lower()==exercise.lower()].copy()
        if not hx.empty:
            last=hx.iloc[0]; best=(hx.assign(volume=hx.sets*hx.reps*hx.weight_kg).sort_values("volume",ascending=False).iloc[0])
            h1,h2,h3=st.columns(3); h1.metric("Last",f"{last.weight_kg:g} kg × {int(last.reps)} × {int(last.sets)}"); h2.metric("Best Volume",f"{best.volume:.0f} kg"); h3.metric("Sessions",len(hx))
            st.caption("Exercise history / تاريخ التمرين")
    with st.form("workout_form",clear_on_submit=True):
        c1,c2,c3,c4=st.columns(4); d=c1.date_input("Date",date.today()); sets=c2.number_input("Sets",1,30,3); reps=c3.number_input("Reps",1,100,8); weight=c4.number_input("Weight (kg)",0.0,500.0,20.0,step=.5)
        rpe=st.number_input("RPE",1.,10.,7.,step=.5)
        if st.form_submit_button("➕ Log Workout",use_container_width=True):
            if not exercise.strip(): st.error("اكتب اسم التمرين.")
            else: insert("workouts",{"date":d.isoformat(),"muscle_group":muscle,"exercise":exercise.strip(),"sets":sets,"reps":reps,"weight_kg":weight,"rpe":rpe}); st.success("Workout logged."); st.rerun()
    df=select_df("workouts")
    if not df.empty:
        df["volume"]=df.sets*df.reps*df.weight_kg
        st.subheader("Progressive Overload")
        selected=st.selectbox("Analyze Exercise",sorted(df.exercise.unique()))
        x=df[df.exercise==selected].copy(); x.date=pd.to_datetime(x.date); x=x.sort_values("date"); fig=go.Figure(); fig.add_trace(go.Scatter(x=x.date,y=x.weight_kg,mode="lines+markers",name="Weight kg")); fig.add_trace(go.Scatter(x=x.date,y=x.volume,mode="lines+markers",name="Volume kg")); fig.update_layout(title=f"{selected} — Weight & Volume",hovermode="x unified"); st.plotly_chart(fig,use_container_width=True)
        st.dataframe(df.sort_values("date",ascending=False),use_container_width=True,hide_index=True)

# ------------------------- Cardio -------------------------
elif page=="🏃 Cardio":
    st.title("🏃 Tactical Cardio & Endurance")
    with st.form("cardio_form",clear_on_submit=True):
        c1,c2,c3=st.columns(3); d=c1.date_input("Date",date.today()); activity=c2.selectbox("Activity",["1500m Time Trial","Interval Sprints","Long Distance Run","Swimming","Ruck Marching","Cycling","Rowing","Other"]); duration=c3.number_input("Duration (min)",.1,1000.,20.)
        c4,c5,c6=st.columns(3); distance=c4.number_input("Distance (km)",0.,500.,1.5,step=.1); hr=c5.number_input("Avg HR",0,250,0); notes=c6.text_input("Notes")
        st.info(f"Automatic pace: **{format_pace(pace(duration,distance))}**")
        if st.form_submit_button("➕ Log Cardio",use_container_width=True): insert("cardio",{"date":d.isoformat(),"activity":activity,"duration_min":duration,"distance_km":distance,"avg_hr":int(hr) if hr else None,"notes":notes,"pace_min_km":pace(duration,distance)}); st.success("Cardio logged."); st.rerun()
    df=select_df("cardio")
    if not df.empty:
        a,b=st.columns(2)
        with a:
            r=df[df.activity=="1500m Time Trial"].copy()
            if not r.empty: r.date=pd.to_datetime(r.date); st.plotly_chart(px.line(r.sort_values("date"),x="date",y="duration_min",markers=True,title="1500m Time — lower is better"),use_container_width=True)
        with b:
            x=df.copy(); x.date=pd.to_datetime(x.date); weekly=x.set_index("date").resample("W").distance_km.sum().reset_index(); st.plotly_chart(px.line(weekly,x="date",y="distance_km",markers=True,title="Weekly Mileage"),use_container_width=True)
        st.dataframe(df,use_container_width=True,hide_index=True)

# ------------------------- Readiness -------------------------
elif page=="🎯 Readiness Tests":
    st.title("🎯 Military Readiness & Tactical Fitness"); st.caption("Illustrative scoring engine — not an official military standard.")
    with st.form("test_form",clear_on_submit=True):
        d=st.date_input("Date",date.today()); c1,c2,c3=st.columns(3); pull=c1.number_input("Pull-ups",0.,100.,10.); push=c2.number_input("Push-ups 2 min",0.,200.,40.); sit=c3.number_input("Sit-ups 2 min",0.,200.,40.); c4,c5,c6=st.columns(3); run=c4.number_input("1500m Time (sec)",1.,3600.,420.); swim=c5.number_input("Swimming (min)",0.,180.,10.); tread=c6.number_input("Water Treading (min)",0.,180.,5.); score=score_readiness(pull,push,sit,run,swim,tread); st.metric("Readiness Score",f"{score:.1f}%")
        if st.form_submit_button("💾 Save Test",use_container_width=True): insert("tests",{"date":d.isoformat(),"pullups":pull,"pushups_2min":push,"situps_2min":sit,"run_1500_sec":run,"swim_min":swim,"water_tread_min":tread,"readiness_score":score}); st.success("Assessment saved."); st.rerun()
    df=select_df("tests")
    if not df.empty: df.date=pd.to_datetime(df.date); st.plotly_chart(px.line(df.sort_values("date"),x="date",y="readiness_score",markers=True,range_y=[0,100],title="Readiness Score Trend"),use_container_width=True); st.dataframe(df,use_container_width=True,hide_index=True)

# ------------------------- Nutrition -------------------------
elif page=="🥗 Nutrition":
    st.title("🥗 Nutrition & Macro Tracker")
    with st.form("meal_form",clear_on_submit=True):
        c1,c2=st.columns(2); d=c1.date_input("Date",date.today()); meal=c2.selectbox("Meal Type",["Breakfast","Lunch","Post-workout Shake","Dinner","Snacks"]); c3,c4,c5,c6=st.columns(4); kcal=c3.number_input("Calories",0.,10000.,500.); protein=c4.number_input("Protein (g)",0.,500.,30.); carbs=c5.number_input("Carbs (g)",0.,1000.,50.); fats=c6.number_input("Fats (g)",0.,500.,15.); desc=st.text_input("Description")
        if st.form_submit_button("➕ Log Meal",use_container_width=True): insert("meals",{"date":d.isoformat(),"meal_type":meal,"calories":kcal,"protein_g":protein,"carbs_g":carbs,"fats_g":fats,"description":desc}); st.success("Meal logged."); st.rerun()
    df=select_df("meals")
    if not df.empty:
        target=st.date_input("Summary date",date.today()); day=df[df.date==target.isoformat()]; totals=day[["calories","protein_g","carbs_g","fats_g"]].sum() if not day.empty else pd.Series([0,0,0,0],index=["calories","protein_g","carbs_g","fats_g"]); c1,c2,c3,c4=st.columns(4); c1.metric("Calories",f"{totals.calories:.0f}"); c2.metric("Protein",f"{totals.protein_g:.0f} g"); c3.metric("Carbs",f"{totals.carbs_g:.0f} g"); c4.metric("Fats",f"{totals.fats_g:.0f} g"); p=pd.DataFrame({"Macro":["Protein","Carbs","Fats"],"Grams":[totals.protein_g,totals.carbs_g,totals.fats_g]}); st.plotly_chart(px.pie(p,names="Macro",values="Grams",hole=.35,title="Macro Distribution"),use_container_width=True); st.dataframe(day.sort_values("id",ascending=False),use_container_width=True,hide_index=True)

# ------------------------- Body -------------------------
elif page=="📏 Body Composition":
    st.title("📏 Body Composition & Transformation")
    with st.form("body_form",clear_on_submit=True):
        c1,c2,c3=st.columns(3); d=c1.date_input("Date",date.today()); weight=c2.number_input("Body Weight (kg)",1.,300.,70.); bf=c3.number_input("Body Fat %",0.,80.,15.); c4,c5,c6=st.columns(3); chest=c4.number_input("Chest (cm)",0.,200.,90.); arm=c5.number_input("Arm (cm)",0.,100.,30.); waist=c6.number_input("Waist (cm)",0.,200.,80.)
        if st.form_submit_button("➕ Save Measurement",use_container_width=True): insert("body",{"date":d.isoformat(),"weight_kg":weight,"body_fat":bf,"chest_cm":chest,"arm_cm":arm,"waist_cm":waist}); st.success("Measurement saved."); st.rerun()
    df=select_df("body")
    if not df.empty: df.date=pd.to_datetime(df.date); df=df.sort_values("date"); df["7d moving avg"]=df.weight_kg.rolling(7,min_periods=1).mean(); st.plotly_chart(px.line(df,x="date",y=["weight_kg","7d moving avg"],markers=True,title="Weight Progression"),use_container_width=True); st.dataframe(df.sort_values("date",ascending=False),use_container_width=True,hide_index=True)

# ------------------------- Data -------------------------
elif page=="🗄️ Data & Export":
    st.title("🗄️ Data & Export")
    dfs={t:select_df(t) for t in TABLES}; table=st.selectbox("Table",TABLES); df=dfs[table]; search=st.text_input("Search")
    if search and not df.empty:
        mask=df.astype(str).apply(lambda col:col.str.contains(search,case=False,na=False)); df=df[mask.any(axis=1)]
    st.dataframe(df,use_container_width=True,hide_index=True)
    c1,c2=st.columns(2); c1.download_button("⬇️ Download CSV",df.to_csv(index=False).encode(),f"{table}.csv","text/csv"); c2.download_button("⬇️ Download Excel",to_excel(dfs),"tactical_fitness.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ------------------------- Settings -------------------------
else:
    st.title("⚙️ Settings")
    c1,c2,c3=st.columns(3); cal=c1.number_input("Daily Calories",500.,10000.,calorie_target,step=50.); prot=c2.number_input("Daily Protein (g)",20.,500.,protein_target,step=5.); wt=c3.number_input("Target Weight (kg)",20.,250.,weight_target,step=.5)
    if st.button("💾 Save Settings",use_container_width=True): save_settings({"calorie_target":cal,"protein_target":prot,"weight_target":wt}); st.success("Settings saved."); st.rerun()
    st.divider(); st.subheader("Account"); st.write(f"Username: **{st.session_state.user.user_metadata.get('username','—')}**"); st.caption("No profile-photo uploads are stored in this version, keeping storage usage minimal.")
