import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import date
import json

# Load credentials from Streamlit secrets (added in Cloud settings)
creds_dict = json.loads(st.secrets["google_credentials"])
creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# Sheet IDs for each league
sheet_ids = {
    "NBA": "1LQDFrmsT2lCHqrvX2V0P8cgQ0wai_GhZLn0aCpeB-Kk",
    "NHL": "1iQPpjGlSlnCWZieBFSxWdv4a_vmoHqLtnVKA86BkLfk",
    "NFL": "your_nfl_sheet_id_here",
    "MLB": "your_mlb_sheet_id_here"
}

st.title("Props Test Website – Big 4 Leagues")

# Sidebar: League and page only (no tier here)
st.sidebar.title("Menu")
league = st.sidebar.selectbox("League", ["NHL", "NBA", "NFL", "MLB"])
page = st.sidebar.selectbox("Go to page", ["Rosters", "Schedules", "Props & Odds"])

# Load the correct sheet for the league
if league not in sheet_ids or not sheet_ids[league]:
    st.error(f"No sheet ID configured for {league}. Add it to the sheet_ids dictionary.")
    st.stop()
sheet_id = sheet_ids[league]
try:
    sheet = client.open_by_key(sheet_id)
except gspread.exceptions.SpreadsheetNotFound:
    st.error(f"Sheet ID '{sheet_id}' not found. Double-check the ID for {league}.")
    st.stop()

# Load tabs (exact names that worked before)
roster_tab = "Rosters"
schedules_tab = "Schedule"

if page == "Rosters":
    st.header(f"{league} Rosters")
    try:
        tab = sheet.worksheet(roster_tab)
        data = tab.get_all_values()
        if len(data) > 0:
            start_row = 0
            if data[0][0].lower().startswith("api key") or not data[0][0].strip():
                start_row = 1
            headers = data[start_row]
            seen = {}
            for i, h in enumerate(headers):
                if h in seen:
                    headers[i] = f"{h} ({seen[h] + 1})"
                    seen[h] += 1
                else:
                    seen[h] = 1
            df = pd.DataFrame(data[start_row + 1:], columns=headers)
        
            # Team filter dropdown on main page
            possible_team_cols = ['Name', 'Full Name', 'Abbreviation', 'Team', 'City', 'Teams']
            team_col = next((col for col in possible_team_cols if col in df.columns), None)
            if team_col:
                def extract_team(team_str):
                    if not team_str or team_str.strip() == '':
                        return None
                    try:
                        # Parse JSON-like string (e.g. "[{\"full_name\":\"Montréal Canadiens\"...}]")
                        teams_list = json.loads(team_str.replace("'", "\""))
                        if isinstance(teams_list, list) and len(teams_list) > 0:
                            return teams_list[0].get('full_name', None)
                    except:
                        pass
                    return team_str # Fallback if not JSON
             
                # Apply extraction and clean
                teams_series = df[team_col].apply(extract_team).dropna().astype(str).str.strip()
                teams_series = teams_series[~teams_series.str.lower().isin(['', 'name', 'team', 'nan'])]
                teams = ["All Teams"] + sorted(teams_series.unique().tolist())
                selected_team = st.selectbox("Filter by Team", teams)
                if selected_team != "All Teams":
                    df = df[df[team_col].apply(extract_team) == selected_team]
            else:
                st.info("No team column found for filtering.")
        
            st.dataframe(
                df,
                use_container_width=True,
                column_config={col: st.column_config.Column(width="medium") for col in df.columns}
            )
        else:
            st.warning(f"No data in '{roster_tab}' tab.")
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Tab '{roster_tab}' not found in {league} sheet. Confirm name is exactly 'Rosters'.")
    except Exception as e:
        st.error(f"Error loading {league} Rosters: {str(e)}")
elif page == "Schedules":
    st.header(f"{league} Schedule")
    try:
        tab = sheet.worksheet(schedules_tab)
        data = tab.get_all_values()
        if len(data) > 0:
            start_row = 0
            if data[0][0].lower().startswith("api key") or not data[0][0].strip():
                start_row = 1
            headers = data[start_row]
            seen = {}
            for i, h in enumerate(headers):
                if h in seen:
                    headers[i] = f"{h} ({seen[h] + 1})"
                    seen[h] += 1
                else:
                    seen[h] = 1
            df = pd.DataFrame(data[start_row + 1:], columns=headers)
        
            date_col = next((col for col in df.columns if 'date' in col.lower()), None)
            if date_col:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                df = df.sort_values(by=date_col).reset_index(drop=True)
        
            st.subheader("Select Date to Filter Games")
            if date_col and not df[date_col].isna().all():
                unique_dates = df[date_col].dt.date.dropna().unique()
                years = sorted(set(d.year for d in unique_dates))
                months = sorted(set(d.month for d in unique_dates))
                days = sorted(set(d.day for d in unique_dates))
             
                selected_year = st.selectbox("Year", [int(y) for y in years])
                filtered_months = sorted(set(d.month for d in unique_dates if d.year == selected_year))
                selected_month = st.selectbox("Month", [int(m) for m in filtered_months])
                filtered_days = sorted(set(d.day for d in unique_dates if d.year == selected_year and d.month == selected_month))
                selected_day = st.selectbox("Day", [int(d) for d in filtered_days])
             
                try:
                    selected_date = date(selected_year, selected_month, selected_day)
                    df_filtered = df[df[date_col].dt.date == selected_date]
                    if df_filtered.empty:
                        st.warning(f"No games on {selected_date}. Try another date.")
                except ValueError:
                    df_filtered = df
                    st.warning("Invalid date selection. Showing all schedules.")
            else:
                df_filtered = df
                st.warning("No valid date column found. Showing all schedules.")
        
            st.dataframe(
                df_filtered,
                use_container_width=True,
                column_config={col: st.column_config.Column(width="medium") for col in df_filtered.columns}
            )
        else:
            st.warning(f"No data in '{schedules_tab}' tab.")
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Tab '{schedules_tab}' not found in {league} sheet. Confirm name is exactly 'Schedule'.")
    except Exception as e:
        st.error(f"Error loading {league} Schedule: {str(e)}")
elif page == "Props & Odds":
    st.header(f"{league} Props & Odds – Best Props")
    tier = st.selectbox("Your Subscription Tier", ["Rookie", "Veteran", "All-Star", "Hall-of-Famer", "Legend"])
    tier_limits = {"Rookie": 5, "Veteran": 15, "All-Star": 25, "Hall-of-Famer": 50, "Legend": 999}
    try:
        # Dynamically list all tabs in the sheet
        all_tabs = [ws.title for ws in sheet.worksheets() if "Props & Odds" in ws.title]  # Filter to only props tabs
        if not all_tabs:
            st.info(f"No Props & Odds tabs found in {league} sheet. Check tab names.")
        else:
            selected_tab = st.selectbox("Select Game Tab", all_tabs)  # Shows all tabs, even "shut off" ones
            tab = sheet.worksheet(selected_tab)
            data = tab.get_all_values()
            if len(data) > 0:
                start_row = 0
                while start_row < len(data) and (not data[start_row] or data[start_row][0].lower().startswith("api key") or all(cell.strip() == '' for cell in data[start_row])):
                    start_row += 1
                headers = data[start_row]
                seen = {}
                for i, h in enumerate(headers):
                    if h in seen:
                        headers[i] = f"{h} ({seen[h] + 1})"
                        seen[h] += 1
                    else:
                        seen[h] = 1
                df = pd.DataFrame(data[start_row + 1:], columns=headers)
         
                # Remove empty rows
                df = df.dropna(how='all')
                df = df[~df.apply(lambda row: row.astype(str).str.strip().eq('').all(), axis=1)]
         
                # Sort by Poisson % if present (optional - keeping your original behavior)
                poisson_col = next((col for col in df.columns if 'poisson' in col.lower()), None)
                if poisson_col:
                    df[poisson_col] = pd.to_numeric(df[poisson_col], errors='coerce')
                    df = df.sort_values(by=poisson_col, ascending=False)
           
                top_n = tier_limits[tier]
                best = df.head(top_n)
           
                st.dataframe(
                    best,
                    use_container_width=True,
                    column_config={col: st.column_config.Column(width="large") for col in best.columns}
                )
                st.write(f"Your tier ({tier}) shows the top {top_n} best props for {selected_tab} (out of {len(df)} valid rows).")
            else:
                st.warning(f"No data in '{selected_tab}' tab.")
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Tab '{selected_tab}' not found in {league} sheet. Confirm tab names match exactly.")
    except Exception as e:
        st.error(f"Error loading {league} Props & Odds: {str(e)}")
