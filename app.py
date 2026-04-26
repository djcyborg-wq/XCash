#!/usr/bin/env python3
"""
XCash - Finanzübersicht Dashboard

Startbefehl: streamlit run app.py
Abhängigkeiten: pip install streamlit pandas plotly
"""

import sys, os, json
import warnings
warnings.filterwarnings('ignore')

try:
    import streamlit as st
    import pandas as pd
    import numpy as np
    import plotly.graph_objects as go
    import plotly.express as px
    from datetime import datetime
except ImportError as e:
    print(f"FEHLER: {e}")
    print("Installieren: pip install streamlit pandas plotly")
    sys.exit(1)

st.set_page_config(page_title="XCash – Finanzübersicht", page_icon="💰", layout="wide", initial_sidebar_state="expanded")

# ============================================
# Konstanten & Mapping
# ============================================
CATEGORY_LABELS = {
    'income.salary': 'Gehalt', 'income.refund': 'Erstattung', 'income.investment': 'Investitionen / Depot',
    'income.bonus': 'Bonus', 'transfer.private': 'Private Überweisungen', 'groceries.supermarket': 'Supermarkt',
    'groceries.discounter': 'Discounter', 'groceries.bio': 'Bio / Feinkost', 'shopping.amazon': 'Amazon',
    'shopping.ebay': 'eBay', 'shopping.clothing': 'Kleidung', 'shopping.electronics': 'Elektronik',
    'shopping.home': 'Wohnen / DIY', 'shopping.drugstore': 'Drogerie', 'housing.utilities': 'Strom / Gas / Heizung',
    'housing.internet': 'Internet / Mobilfunk', 'housing.taxes': 'Steuern / Gebühren',
    'housing.insurance.home': 'Wohnversicherung', 'housing.rent': 'Miete', 'insurance.life': 'Lebensversicherung',
    'insurance.car': 'Kfz-Versicherung', 'insurance.health': 'Krankenversicherung', 'transport.fuel': 'Tanken',
    'transport.public': 'ÖPNV / Bahn', 'transport.parking': 'Parken', 'transport.maintenance': 'Wartung',
    'dining.bakery': 'Bäckerei', 'dining.restaurant': 'Restaurant / Café', 'dining.fast_food': 'Fast Food',
    'entertainment.streaming': 'Streaming', 'entertainment.travel': 'Reise / Urlaub',
    'entertainment.sports': 'Sport / Fitness', 'entertainment.hobby': 'Hobby / Freizeit',
    'health.pharmacy': 'Apotheke', 'health.doctor': 'Arzt / Klinik', 'finance.investment': 'Investitionen / Depot',
    'finance.fees': 'Bankgebühren', 'finance.interest': 'Zinsen', 'subscriptions.software': 'Software-Abos',
    'subscriptions.membership': 'Mitgliedschaften', 'travel.foreign_card': 'Auslandskartenzahlung',
    'fees.atm': 'Bargeld / ATM', 'fees.other': 'Sonstige Gebühren', 'uncategorized': 'Nicht kategorisiert',
    'fees.bank': 'Bankgebühren',
    'banking.transaction': 'Banktransaktion',
    'payment.card': 'Kartenzahlung',
    'payment.paypal': 'PayPal',
    'payment.provider': 'Zahlungsdienstleister',
    'utilities.telecom': 'Telekommunikation',
    'transport.maintenance': 'Werkstatt / Wartung',
}

FREQUENCY_LABELS = {'monthly': 'Monatlich', 'weekly': 'Wöchentlich', 'irregular': 'Unregelmäßig'}
ANOMALY_TYPE_LABELS = {
    'category_amount_outlier': 'Kategorie-Ausreißer', 'merchant_amount_outlier': 'Händler-Ausreißer',
    'possible_duplicate_charge': 'Mögliche Doppelabbuchung', 'large_single_transaction': 'Große Einzelzahlung',
}
SEVERITY_LABELS = {'high': 'Hoch', 'medium': 'Mittel', 'low': 'Niedrig'}
MONTH_LABELS = {1:'Jan',2:'Feb',3:'Mär',4:'Apr',5:'Mai',6:'Jun',7:'Jul',8:'Aug',9:'Sep',10:'Okt',11:'Nov',12:'Dez'}
CHART_COLORS = ['#4f46e5', '#06b6d4', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6', '#f97316']
COMPACT_CATEGORY_LABELS = {
    'income': 'Einnahmen',
    'groceries': 'Lebensmittel',
    'shopping': 'Shopping',
    'transport': 'Mobilität',
    'housing': 'Wohnen',
    'insurance': 'Versicherungen',
    'dining': 'Essen & Trinken',
    'entertainment': 'Freizeit',
    'subscriptions': 'Abos',
    'payment': 'Zahlungen',
    'banking': 'Banking',
    'fees': 'Gebühren',
    'transfer': 'Überweisungen',
    'travel': 'Reise',
    'utilities': 'Versorger',
    'uncategorized': 'Nicht kategorisiert',
}

def get_clabel(code): return CATEGORY_LABELS.get(code, str(code))
def get_compact_label(code): return COMPACT_CATEGORY_LABELS.get(code, str(code))
def get_flabel(f): return FREQUENCY_LABELS.get(f, str(f))
def get_atlabel(t): return ANOMALY_TYPE_LABELS.get(t, str(t))
def get_slabel(s): return SEVERITY_LABELS.get(s, str(s))
def format_euro(v):
    try:
        if v is None or pd.isna(v): return "-"
        val = float(v)
        fmt = f"{abs(val):,.2f}".replace(",","X").replace(".", ",").replace("X", ".")
        return f"{fmt} €" if val >= 0 else f"-{fmt} €"
    except: return "-"
def format_pct(v):
    try:
        if v is None or pd.isna(v): return "-"
        return f"{float(v)*100:.0f}%" if float(v) <= 1 else f"{float(v):.0f}%"
    except: return "-"
def format_date(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return ""
    try:
        if isinstance(v, str):
            for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y"):
                try: return datetime.strptime(v.strip(), fmt).strftime("%d.%m.%Y")
                except: continue
            return v
        if hasattr(v, "strftime"): return v.strftime("%d.%m.%Y")
        return pd.Timestamp(v).strftime("%d.%m.%Y")
    except: return str(v)

def to_compact_category(cat):
    if cat is None or (isinstance(cat, float) and pd.isna(cat)):
        return 'uncategorized'
    c = str(cat).strip().lower()
    if not c:
        return 'uncategorized'
    if c == 'uncategorized':
        return 'uncategorized'
    if '.' in c:
        return c.split('.', 1)[0]
    return c

def _parse_mixed_number(value):
    """Konvertiert Zahlen robust fuer DE/EN Formate."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return np.nan
    s = str(value).strip().replace(" ", "")
    if not s:
        return np.nan
    # Bereits numerisch
    try:
        if isinstance(value, (int, float, np.number)):
            return float(value)
    except Exception:
        pass
    # DE Format: 1.234,56
    if "." in s and "," in s and s.rfind(",") > s.rfind("."):
        s = s.replace(".", "").replace(",", ".")
    # EN Format: 1,234.56
    elif "." in s and "," in s and s.rfind(".") > s.rfind(","):
        s = s.replace(",", "")
    # Nur Komma: 123,45
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    # Nur Punkt: 1234.56 bleibt unveraendert
    try:
        return float(s)
    except Exception:
        return np.nan

def parse_german_number_series(series):
    """Konvertiert Zahlen robust (z.B. 1.234,56 und 1234.56)."""
    if series is None:
        return series
    return series.apply(_parse_mixed_number)

def format_reason(reason, anomaly_type=None):
    """Uebersetzt/verdichtet technische Anomalie-Begruendungen."""
    if reason is None or (isinstance(reason, float) and pd.isna(reason)):
        return ""
    txt = str(reason).strip()
    low = txt.lower()
    if "deviates from category median" in low:
        return "Betrag weicht deutlich vom typischen Kategorieniveau ab."
    if "deviates from merchant median" in low:
        return "Betrag weicht deutlich vom typischen Empfänger-Niveau ab."
    if "possible duplicate charge" in low or "duplicate" in low:
        return "Mögliche Doppelabbuchung erkannt."
    if "large single transaction" in low:
        return "Ungewöhnlich große Einzelbuchung."
    if anomaly_type == "category_amount_outlier":
        return "Auffälliger Betrag im Vergleich zu ähnlichen Buchungen dieser Kategorie."
    if anomaly_type == "merchant_amount_outlier":
        return "Auffälliger Betrag im Vergleich zu früheren Buchungen bei diesem Empfänger."
    if anomaly_type == "possible_duplicate_charge":
        return "Mögliche Doppelabbuchung erkannt."
    if anomaly_type == "large_single_transaction":
        return "Ungewöhnlich große Einzelbuchung."
    return txt

def repair_display_text(value):
    """Repariert haeufige Zeichenartefakte fuer die UI-Anzeige."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return value
    text = str(value)
    replacements = {
        'Echtzeit�berweisung': 'Echtzeitüberweisung',
        '�berweisung': 'Überweisung',
        'Empf�nger': 'Empfänger',
        'Grose': 'Große',
        'Grundsteue r': 'Grundsteuer',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

@st.cache_data
def load_data():
    data = {'transactions': pd.DataFrame(), 'recurring': pd.DataFrame()}
    fcsv = "data/final_transactions.csv"
    if os.path.exists(fcsv):
        try:
            df = pd.read_csv(fcsv, encoding='utf-8')
            for c in df.columns:
                cl = c.lower()
                if 'date' in cl and 'booking' not in cl and 'value' not in cl: df = df.rename(columns={c:'date'})
                elif 'booking' in cl and 'date' in cl: df = df.rename(columns={c:'booking_date'})
                elif 'value' in cl and 'date' in cl: df = df.rename(columns={c:'value_date'})
                elif 'counterparty' in cl: df = df.rename(columns={c:'counterparty'})
                elif 'amount' in cl and 'abs' not in cl: df = df.rename(columns={c:'amount'})
                elif 'category' in cl: df = df.rename(columns={c:'category'})
                elif 'booking_text' in cl or 'buchungstext' in cl: df = df.rename(columns={c:'booking_text'})
                elif 'purpose' in cl or 'verwendungszweck' in cl: df = df.rename(columns={c:'purpose'})
            if 'date' not in df.columns:
                df['date'] = df.get('booking_date', df.get('value_date', pd.NaT))
            for col in ['date','booking_date','value_date']:
                if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce')
            if 'amount' in df.columns:
                df['amount'] = parse_german_number_series(df['amount'])
            if 'balance' in df.columns:
                df['balance'] = parse_german_number_series(df['balance'])
            acols = [c for c in df.columns if 'auftrag' in c.lower() or 'empf' in c.lower()]
            if acols and 'counterparty' in df.columns:
                mask = df['counterparty'].isna() | (df['counterparty'].astype(str).str.strip() == '')
                df.loc[mask, 'counterparty'] = df.loc[mask, acols[0]]
            elif acols: df['counterparty'] = df[acols[0]]
            data['transactions'] = df
        except Exception as e: st.error(f"Lade-Fehler: {e}")
    rcsv = "outputs/recurring_payments.csv"
    if os.path.exists(rcsv):
        try: data['recurring'] = pd.read_csv(rcsv, encoding='utf-8')
        except: data['recurring'] = pd.DataFrame()
    acsv = "outputs/anomalies.csv"
    if os.path.exists(acsv):
        try: st.session_state['anomalies'] = pd.read_csv(acsv, encoding='utf-8')
        except: st.session_state['anomalies'] = pd.DataFrame()
    else: st.session_state['anomalies'] = pd.DataFrame()
    return data

def get_quick_ranges(df):
    if df.empty or 'date' not in df.columns: return {}
    mn, mx = df['date'].min(), df['date'].max()
    if pd.isna(mn) or pd.isna(mx): return {}
    today = pd.Timestamp('today').normalize()
    ranges = {'Gesamter Zeitraum':(mn, mx), 'Aktueller Monat':(today.replace(day=1), today)}
    fdlm = today.replace(day=1) - pd.Timedelta(days=1)
    ranges['Letzter Monat'] = (fdlm.replace(day=1), fdlm)
    for m in [3,6,12]: ranges[f'Letzte {m} Monate'] = (today - pd.DateOffset(months=m), today)
    for y in sorted([d for d in df['date'].dropna().dt.year.unique() if not pd.isna(d)]):
        ranges[f'Jahr {int(y)}'] = (pd.Timestamp(f'{int(y)}-01-01'), pd.Timestamp(f'{int(y)}-12-31'))
    return ranges

def make_filters(df):
    st.sidebar.title("⚙️ Filter")
    if df.empty: st.sidebar.warning("Keine Daten."); return {}
    f = {}
    st.sidebar.subheader("Zeitraum")
    qr = get_quick_ranges(df)
    if qr:
        qk = st.sidebar.selectbox("Schnellwahl", options=list(qr.keys()), index=0)
        f['qrange'], f['qranges'] = qk, qr
        sd, ed = qr[qk]
    else: sd = ed = pd.Timestamp.today()
    st.sidebar.caption("Oder manuell:")
    if 'date' in df.columns and df['date'].notna().any():
        mind, maxd = df['date'].min().date(), df['date'].max().date()
        # Default auf gueltigen Bereich beschraenken
        if ed.date() > maxd: ed = pd.Timestamp(maxd)
        if sd.date() < mind: sd = pd.Timestamp(mind)
        if sd > ed: sd, ed = pd.Timestamp(mind), pd.Timestamp(maxd)
        dr = st.sidebar.date_input(
            "Datumsbereich",
            value=(sd.date(), ed.date()),
            min_value=mind,
            max_value=maxd,
            key='drange'
        )
        if isinstance(dr, tuple):
            if len(dr) == 2:
                start_date, end_date = dr[0], dr[1]
            elif len(dr) == 1:
                # Waehlt der Nutzer gerade nur das Startdatum, behalten wir das letzte Ende bei.
                start_date = dr[0]
                end_date = st.session_state.get('drange_last_end', ed.date())
            else:
                start_date, end_date = sd.date(), ed.date()
        else:
            start_date = end_date = dr
        start_ts, end_ts = pd.Timestamp(start_date), pd.Timestamp(end_date)
        if start_ts > end_ts:
            start_ts, end_ts = end_ts, start_ts
        f['sd'], f['ed'] = start_ts, end_ts
        st.session_state['drange_last_start'] = f['sd'].date()
        st.session_state['drange_last_end'] = f['ed'].date()
    st.sidebar.markdown("---")
    st.sidebar.subheader("Betrag")
    f['ttype'] = st.sidebar.radio("Typ", ["Alle","Einnahmen","Ausgaben"], horizontal=True)
    f['minamt'] = st.sidebar.number_input("Mindestbetrag (€)", min_value=0.0, value=0.0, step=10.0)
    st.sidebar.markdown("---")
    st.sidebar.subheader("Kategorien")
    f['category_mode'] = st.sidebar.radio(
        "Ansicht",
        ["Zusammengefasst", "Detailliert"],
        horizontal=True
    )
    if 'category' in df.columns:
        if f['category_mode'] == "Zusammengefasst":
            cats = sorted(df['category'].dropna().astype(str).map(to_compact_category).unique())
            label_fn = get_compact_label
        else:
            cats = sorted([c for c in df['category'].dropna().unique() if str(c).strip()])
            label_fn = get_clabel
        if cats:
            select_all = st.sidebar.checkbox("Alle Kategorien auswählen", value=True, key='cats_all')
            default_sel = cats if select_all else cats[:min(10, len(cats))]
            sel = st.sidebar.multiselect("Kategorien", options=cats, default=default_sel, format_func=label_fn)
            f['cats'] = sel if sel else cats
        else:
            st.sidebar.info("Keine Kategorien.")
            f['cats'] = []
    else:
        f['cats'] = []
    st.sidebar.markdown("---")
    st.sidebar.subheader("Anzeigen")
    f['show_anom'] = st.sidebar.checkbox("Anomalien", True, key='sa')
    f['show_rec'] = st.sidebar.checkbox("Regelmäßige Zahlungen", True, key='sr')
    return f

def apply_filters(df, f):
    if df.empty: return df
    r = df.copy()
    if 'date' in r.columns:
        # Manueller Bereich hat Vorrang, Schnellwahl dient nur als Default.
        if 'sd' in f and 'ed' in f:
            r = r[(r['date']>=f['sd']) & (r['date']<=f['ed'])]
        elif f.get('qrange') and f['qrange'] in f.get('qranges',{}):
            s,e = f['qranges'][f['qrange']]
            r = r[(r['date']>=s) & (r['date']<=e)]
    if f.get('ttype')=='Einnahmen': r=r[r['amount']>0]
    elif f.get('ttype')=='Ausgaben': r=r[r['amount']<0]
    if f.get('cats'):
        if f.get('category_mode') == "Zusammengefasst":
            mapped = r['category'].astype(str).map(to_compact_category)
            r = r[mapped.isin(f['cats'])]
        else:
            r = r[r['category'].isin(f['cats'])]
    if f.get('minamt',0)>0: r=r[r['amount'].abs()>=f['minamt']]
    return r

def calc_kpis(df, anom_df):
    if df.empty or 'amount' not in df.columns: return {}
    inc = df[df['amount']>0]['amount'].sum()
    exp = df[df['amount']<0]['amount'].sum()
    net = inc+exp
    k = {'Einnahmen':inc,'Ausgaben':abs(exp),'Netto':net,
         'Sparrate':(net/inc*100) if inc!=0 else 0,
         'Transaktionen':len(df)}
    k['Anomalien'] = len(anom_df)
    k['Anomalien (Hoch)'] = len(anom_df[anom_df['severity']=='high']) if not anom_df.empty else 0
    k['Bester Monat'] = k['Schwächster Monat'] = '-'
    if not df.empty and 'date' in df.columns:
        dm = df.copy(); dm['month'] = dm['date'].dt.to_period('M')
        mon = dm.groupby('month')['amount'].sum().reset_index()
        if not mon.empty:
            b = mon.loc[mon['amount'].idxmax()]
            w = mon.loc[mon['amount'].idxmin()]
            k['Bester Monat'] = f"{b['month']}: {format_euro(b['amount'])}"
            k['Schwächster Monat'] = f"{w['month']}: {format_euro(w['amount'])}"
    expdf = df[df['amount']<0].copy()
    k['Größte Kategorie'] = k['Größter Empfänger'] = '-'
    if not expdf.empty:
        if 'category' in expdf.columns:
            cs = expdf.groupby('category')['amount'].sum().sort_values()
            if not cs.empty:
                k['Größte Kategorie'] = f"{get_clabel(cs.index[0])} ({format_euro(cs.iloc[0])})"
        if 'counterparty' in expdf.columns:
            rs = expdf.groupby('counterparty')['amount'].sum().sort_values()
            if not rs.empty:
                k['Größter Empfänger'] = f"{rs.index[0][:30]} ({format_euro(rs.iloc[0])})"
    return k

def make_charts(df):
    if df.empty or 'date' not in df.columns: return
    dc = df.copy()
    dc['month'] = dc['date'].dt.to_period('M')
    if 'balance' in dc.columns:
        dc['balance'] = parse_german_number_series(dc['balance'])
    st.subheader("Monatlicher Cashflow")
    mon = dc.groupby('month')['amount'].sum().reset_index()
    mon.columns = ['Monat','Cashflow']
    mon['Label'] = mon['Monat'].apply(lambda x: f"{MONTH_LABELS.get(x.month,str(x.month))} {x.year}")
    fig = px.line(
        mon, x='Label', y='Cashflow', title='', markers=True,
        color_discrete_sequence=[CHART_COLORS[0]]
    )
    fig.add_hline(y=0, line_dash="dash", line_color="grey")
    fig.update_layout(yaxis_title="€", xaxis_title="")
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>Cashflow: %{y:,.2f} €<extra></extra>",
        line=dict(width=3),
        marker=dict(size=8)
    )
    st.plotly_chart(fig, use_container_width=True)
    if 'balance' in dc.columns and dc['balance'].notna().any():
        st.subheader("Kontostand-Verlauf")
        # Kontostand ist Saldo nach Buchung -> pro Datum letzte Buchung verwenden.
        db = dc.dropna(subset=['date', 'balance']).sort_values('date')
        db = db.groupby('date', as_index=False).tail(1).sort_values('date')
        if not db.empty:
            fb = px.line(
                db, x='date', y='balance', title='', markers=False,
                color_discrete_sequence=[CHART_COLORS[2]]
            )
            fb.update_layout(yaxis_title="Kontostand (€)", xaxis_title="")
            fb.update_traces(hovertemplate="<b>%{x|%d.%m.%Y}</b><br>Kontostand: %{y:,.2f} €<extra></extra>", line=dict(width=3))
            st.plotly_chart(fb, use_container_width=True)
    c1,c2 = st.columns(2)
    exp = dc[dc['amount']<0].copy()
    with c1:
        st.subheader("Ausgaben nach Kategorie")
        if not exp.empty and 'category' in exp.columns:
            cs = exp.groupby('category')['amount'].sum().abs().sort_values(ascending=False).head(10)
            if len(cs)>0:
                lbs = [get_clabel(str(c)) for c in cs.index]
                fcp = px.pie(values=cs.values, names=lbs, title='', hole=0.4, color_discrete_sequence=CHART_COLORS)
                fcp.update_traces(hovertemplate="<b>%{label}</b><br>Betrag: %{value:,.2f} €<br>Anteil: %{percent}<extra></extra>")
                st.plotly_chart(fcp, use_container_width=True)
    with c2:
        st.subheader("Top 10 Empfänger")
        if not exp.empty and 'counterparty' in exp.columns:
            top = exp.groupby('counterparty')['amount'].sum().abs().sort_values(ascending=False).head(10)
            if len(top)>0:
                fr = px.bar(
                    y=top.index, x=top.values, orientation='h', title='',
                    color=top.values, color_continuous_scale='Turbo'
                )
                fr.update_layout(yaxis_title="", xaxis_title="€", yaxis={'categoryorder':'total ascending'})
                fr.update_traces(hovertemplate="<b>%{y}</b><br>Ausgaben: %{x:,.2f} €<extra></extra>")
                st.plotly_chart(fr, use_container_width=True)
    st.subheader("Einnahmen vs Ausgaben")
    incm = dc[dc['amount']>0].groupby('month')['amount'].sum().abs().reset_index()
    expm = dc[dc['amount']<0].groupby('month')['amount'].sum().abs().reset_index()
    if not incm.empty and not expm.empty:
        incm['Label'] = incm['month'].apply(lambda x: f"{MONTH_LABELS.get(x.month,str(x.month))} {x.year}")
        expm['Label'] = expm['month'].apply(lambda x: f"{MONTH_LABELS.get(x.month,str(x.month))} {x.year}")
        fgc = go.Figure()
        fgc.add_trace(go.Bar(
            name='Einnahmen', x=incm['Label'], y=incm['amount'],
            marker_color=CHART_COLORS[2],
            hovertemplate="<b>%{x}</b><br>Einnahmen: %{y:,.2f} €<extra></extra>"
        ))
        fgc.add_trace(go.Bar(
            name='Ausgaben', x=expm['Label'], y=expm['amount'],
            marker_color=CHART_COLORS[4],
            hovertemplate="<b>%{x}</b><br>Ausgaben: %{y:,.2f} €<extra></extra>"
        ))
        fgc.update_layout(barmode='group', yaxis_title="€", xaxis_title="")
        st.plotly_chart(fgc, use_container_width=True)

def detail_analysis(df):
    st.subheader("🔍 Detailanalyse")
    if df.empty:
        st.info("Keine Daten für Detailanalyse.")
        return
    atype = st.selectbox("Analyse-Typ", ["Kategorie analysieren", "Empfänger analysieren", "Freitextsuche"])
    st.markdown("---")
    if atype == "Kategorie analysieren":
        if 'category' not in df.columns:
            st.warning("Keine Kategorie-Spalte.")
            return
        cats = sorted([c for c in df['category'].dropna().unique() if str(c).strip()])
        if not cats:
            st.info("Keine Kategorien.")
            return
        select_all_detail = st.checkbox("Alle Kategorien (Detailanalyse)", value=False, key='detail_all_cats')
        if select_all_detail:
            selected_cats = cats
        else:
            selected_cats = st.multiselect("Kategorien", options=cats, default=cats[:1], format_func=get_clabel, key='detail_multi_cats')
        if not selected_cats:
            st.info("Bitte mindestens eine Kategorie auswählen.")
            return
        sub = df[df['category'].isin(selected_cats)].copy()
        if sub.empty:
            st.info("Keine Buchungen für diese Kategorie.")
            return
        k = sub['amount'].sum()
        inc = sub[sub['amount']>0]['amount'].sum()
        exp = sub[sub['amount']<0]['amount'].sum()
        st.metric("Anzahl Buchungen", len(sub))
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.metric("Einnahmen", format_euro(inc))
        with c2: st.metric("Ausgaben", format_euro(abs(exp)))
        with c3: st.metric("Netto", format_euro(k))
        with c4: st.metric("Ø Betrag", format_euro(k/len(sub)) if len(sub)>0 else "-")
        if 'amount' in sub.columns and len(sub)>0:
            maxi = sub.loc[sub['amount'].idxmax()]
            st.write(f"**Größte Buchung:** {format_euro(maxi['amount'])} am {format_date(maxi.get('date',''))} ({maxi.get('counterparty','')})")
        st.markdown("---")
        st.write("**Monatsentwicklung**")
        subm = sub.copy()
        subm['month'] = subm['date'].dt.to_period('M')
        submon = subm.groupby('month')['amount'].sum().reset_index()
        if not submon.empty:
            submon['Label'] = submon['month'].apply(lambda x: f"{MONTH_LABELS.get(x.month,str(x.month))} {x.year}")
            fsc = px.bar(
                submon, x='Label', y='amount', title='',
                color='amount', color_continuous_scale='RdYlGn'
            )
            fsc.update_layout(yaxis_title="€", xaxis_title="")
            fsc.update_traces(hovertemplate="<b>%{x}</b><br>Saldo: %{y:,.2f} €<extra></extra>")
            st.plotly_chart(fsc, use_container_width=True)
        st.markdown("---")
        st.write("**Top 10 Empfänger in dieser Kategorie**")
        if 'counterparty' in sub.columns:
            topc = sub.groupby('counterparty')['amount'].sum().sort_values()
            if not topc.empty:
                ftc = px.bar(
                    y=topc.index, x=np.abs(topc.values), orientation='h', title='',
                    color=np.abs(topc.values), color_continuous_scale='Viridis'
                )
                ftc.update_layout(yaxis_title="", xaxis_title="€", xaxis={'categoryorder':'total ascending'})
                ftc.update_traces(hovertemplate="<b>%{y}</b><br>Betrag: %{x:,.2f} €<extra></extra>")
                st.plotly_chart(ftc, use_container_width=True)
        st.markdown("---")
        st.write("**Alle Buchungen**")
        if len(selected_cats) == 1:
            table_title = f"Buchungen: {get_clabel(selected_cats[0])}"
        else:
            table_title = f"Buchungen: {len(selected_cats)} Kategorien"
        show_table(sub, table_title)
    elif atype == "Empfänger analysieren":
        if 'counterparty' not in df.columns:
            st.warning("Keine Empfänger-Spalte.")
            return
        all_rec = sorted([c for c in df['counterparty'].dropna().unique() if str(c).strip()])
        if not all_rec:
            st.info("Keine Empfänger.")
            return
        rec_search = st.selectbox("Empfänger (Teiltreffer möglich)", options=[""] + all_rec)
        if not rec_search:
            return
        matches = df[df['counterparty'].str.contains(rec_search, case=False, na=False)]
        if matches.empty:
            st.info("Keine Treffer.")
            return
        st.success(f"Gefunden: {len(matches)} Buchungen für '{rec_search}'")
        k = matches['amount'].sum()
        inc = matches[matches['amount']>0]['amount'].sum()
        exp = matches[matches['amount']<0]['amount'].sum()
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.metric("Anzahl", len(matches))
        with c2: st.metric("Einnahmen", format_euro(inc))
        with c3: st.metric("Ausgaben", format_euro(abs(exp)))
        with c4: st.metric("Netto", format_euro(k))
        c5,c6 = st.columns(2)
        with c5: st.metric("Ø Betrag", format_euro(k/len(matches)) if len(matches)>0 else "-")
        with c6:
            if 'date' in matches.columns:
                st.metric("Erste Buchung", format_date(matches['date'].min()))
                st.metric("Letzte Buchung", format_date(matches['date'].max()))
        st.markdown("---")
        st.write("**Kategorien dieses Empfängers**")
        if 'category' in matches.columns:
            cats_emp = matches.groupby('category').agg({'amount':['sum','count']}).reset_index()
            cats_emp.columns = ['Kategorie','Summe','Anzahl']
            cats_emp['Summe'] = cats_emp['Summe'].apply(format_euro)
            st.dataframe(cats_emp, use_container_width=True, hide_index=True)
            if len(cats_emp) > 1:
                st.warning("⚠ Dieser Empfänger hat mehrere Kategorien. Bitte prüfen, ob Falschkategorisierungen vorliegen.")
        st.markdown("---")
        st.write("**Monatsentwicklung**")
        if 'date' in matches.columns:
            mtm = matches.copy()
            mtm['month'] = mtm['date'].dt.to_period('M')
            monemp = mtm.groupby('month')['amount'].sum().reset_index()
            if not monemp.empty:
                monemp['Label'] = monemp['month'].apply(lambda x: f"{MONTH_LABELS.get(x.month,str(x.month))} {x.year}")
                fme = px.bar(
                    monemp, x='Label', y='amount', title='',
                    color='amount', color_continuous_scale='Plasma'
                )
                fme.update_layout(yaxis_title="€", xaxis_title="")
                fme.update_traces(hovertemplate="<b>%{x}</b><br>Saldo: %{y:,.2f} €<extra></extra>")
                st.plotly_chart(fme, use_container_width=True)
        st.markdown("---")
        st.write("**Alle Treffer**")
        show_table(matches, f"Treffer: {rec_search}")
        st.markdown("---")
        csv = matches.to_csv(index=False, encoding='utf-8')
        st.download_button("📥 Detailanalyse als CSV exportieren", csv, f"detail_{rec_search[:20]}.csv", "text/csv", key='dlcsv')
    else:
        st.write("Suche in: Empfänger, Buchungstext, Verwendungszweck, Kategorie")
        query = st.text_input("Suchbegriff")
        if query:
            mask = pd.Series(False, index=df.index)
            if 'counterparty' in df.columns:
                mask |= df['counterparty'].astype(str).str.contains(query, case=False, na=False)
            if 'purpose' in df.columns:
                mask |= df['purpose'].astype(str).str.contains(query, case=False, na=False)
            if 'booking_text' in df.columns:
                mask |= df['booking_text'].astype(str).str.contains(query, case=False, na=False)
            if 'category' in df.columns:
                mask |= df['category'].astype(str).str.contains(query, case=False, na=False)
            res = df[mask]
            if res.empty:
                st.info("Keine Treffer.")
            else:
                st.success(f"Gefunden: {len(res)} Buchungen")
                c1,c2 = st.columns(2)
                with c1: st.metric("Summe Einnahmen", format_euro(res[res['amount']>0]['amount'].sum()))
                with c2: st.metric("Summe Ausgaben", format_euro(abs(res[res['amount']<0]['amount'].sum())))
                show_table(res, f"Suchergebnis: {query}")

def show_table(data, title=""):
    if data.empty:
        st.info("Keine Daten.")
        return
    d = data.copy()
    col_order = []
    col_config = {}
    if 'date' in d.columns:
        col_order.append('Datum')
        d['Datum'] = d['date']
        col_config['Datum'] = st.column_config.DateColumn("Datum", format="DD.MM.YYYY")
    if 'counterparty' in d.columns:
        col_order.append('Empfänger / Auftraggeber')
        d['Empfänger / Auftraggeber'] = d['counterparty'].apply(repair_display_text)
        col_config['Empfänger / Auftraggeber'] = st.column_config.TextColumn("Empfänger / Auftraggeber")
    if 'category' in d.columns:
        col_order.append('Kategorie')
        d['Kategorie'] = d['category'].apply(get_clabel)
        col_config['Kategorie'] = st.column_config.TextColumn("Kategorie")
    if 'amount' in d.columns:
        col_order.append('Betrag')
        d['Betrag'] = d['amount']
        col_config['Betrag'] = st.column_config.NumberColumn("Betrag", format="%.2f €")
    if 'booking_text' in d.columns:
        col_order.append('Buchungstext')
        d['Buchungstext'] = d['booking_text'].apply(repair_display_text)
        col_config['Buchungstext'] = st.column_config.TextColumn("Buchungstext")
    if 'purpose' in d.columns:
        col_order.append('Verwendungszweck')
        d['Verwendungszweck'] = d['purpose'].apply(repair_display_text)
        col_config['Verwendungszweck'] = st.column_config.TextColumn("Verwendungszweck")
    if 'anomaly_type' in d.columns:
        col_order.append('Anomalie-Typ')
        d['Anomalie-Typ'] = d['anomaly_type'].apply(get_atlabel)
        col_config['Anomalie-Typ'] = st.column_config.TextColumn("Anomalie-Typ")
    if 'severity' in d.columns:
        col_order.append('Schweregrad')
        d['Schweregrad'] = d['severity'].apply(get_slabel)
        col_config['Schweregrad'] = st.column_config.TextColumn("Schweregrad")
    if 'reason' in d.columns:
        col_order.append('Begründung')
        d['Begründung'] = d.apply(lambda r: format_reason(r.get('reason'), r.get('anomaly_type')), axis=1)
        col_config['Begründung'] = st.column_config.TextColumn("Begründung")
    if 'confidence' in d.columns:
        col_order.append('Sicherheit')
        d['Sicherheit'] = pd.to_numeric(d['confidence'], errors='coerce').fillna(0) * 100
        col_config['Sicherheit'] = st.column_config.ProgressColumn("Sicherheit", min_value=0, max_value=100, format="%.0f%%")
    if 'avg_amount' in d.columns:
        col_order.append('Durchschnittsbetrag')
        d['Durchschnittsbetrag'] = d['avg_amount']
        col_config['Durchschnittsbetrag'] = st.column_config.NumberColumn("Durchschnittsbetrag", format="%.2f €")
    if 'std_amount' in d.columns:
        col_order.append('Schwankung')
        d['Schwankung'] = d['std_amount']
        col_config['Schwankung'] = st.column_config.NumberColumn("Schwankung", format="%.2f €")
    if 'occurrences' in d.columns:
        col_order.append('Anzahl')
        d['Anzahl'] = d['occurrences']
        col_config['Anzahl'] = st.column_config.NumberColumn("Anzahl", format="%d")
    if 'frequency' in d.columns:
        col_order.append('Häufigkeit')
        d['Häufigkeit'] = d['frequency'].apply(get_flabel)
        col_config['Häufigkeit'] = st.column_config.TextColumn("Häufigkeit")
    if 'first_date' in d.columns:
        col_order.append('Erstes Datum')
        d['Erstes Datum'] = d['first_date']
        col_config['Erstes Datum'] = st.column_config.DateColumn("Erstes Datum", format="DD.MM.YYYY")
    if 'last_date' in d.columns:
        col_order.append('Letztes Datum')
        d['Letztes Datum'] = d['last_date']
        col_config['Letztes Datum'] = st.column_config.DateColumn("Letztes Datum", format="DD.MM.YYYY")
    cols_to_show = [c for c in col_order if c in d.columns]
    st.caption(title if title else "")
    st.dataframe(d[cols_to_show], column_config=col_config, use_container_width=True, hide_index=True)

def main():
    st.title("💰 XCash – Finanzübersicht")
    st.caption("Buchungen, Auswertungen und Detailanalyse")
    data = load_data()
    df = data.get('transactions', pd.DataFrame())
    recurring_df = data.get('recurring', pd.DataFrame())
    anomalies_df = st.session_state.get('anomalies', pd.DataFrame())
    if df.empty:
        st.warning("⚠ Keine Transaktionsdaten gefunden. Bitte 'data/final_transactions.csv' prüfen.")
        return
    filters = make_filters(df)
    filtered_df = apply_filters(df, filters)
    if 'sd' in filters and 'ed' in filters:
        period_label = f"{filters['sd'].strftime('%d.%m.%Y')} - {filters['ed'].strftime('%d.%m.%Y')}"
    elif filters.get('qrange') and filters.get('qranges') and filters['qrange'] in filters['qranges']:
        s, e = filters['qranges'][filters['qrange']]
        period_label = f"{pd.Timestamp(s).strftime('%d.%m.%Y')} - {pd.Timestamp(e).strftime('%d.%m.%Y')}"
    else:
        period_label = "Gesamter Zeitraum"
    st.info(
        f"📊 Aktive Auswahl: {len(filtered_df)} von {len(df)} Transaktionen "
        f"({len(filtered_df)/len(df)*100:.1f}%) | Zeitraum: {period_label}"
    )
    kpis = calc_kpis(filtered_df, anomalies_df)
    col1,col2,col3,col4,col5,col6 = st.columns(6)
    with col1: st.metric("Einnahmen", format_euro(kpis.get('Einnahmen',0)))
    with col2: st.metric("Ausgaben", format_euro(kpis.get('Ausgaben',0)))
    with col3: st.metric("Netto", format_euro(kpis.get('Netto',0)), format_pct(kpis.get('Sparrate',0)))
    with col4: st.metric("Transaktionen", kpis.get('Transaktionen',0))
    with col5: st.metric("Anomalien", kpis.get('Anomalien',0))
    with col6: st.metric("Hoch", kpis.get('Anomalien (Hoch)',0))
    st.subheader("Finanzielle Kurzdiagnose")
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f"**Bester Monat**<br><small>{kpis.get('Bester Monat','-')}</small>", unsafe_allow_html=True)
    with c2: st.markdown(f"**Schwächster Monat**<br><small>{kpis.get('Schwächster Monat','-')}</small>", unsafe_allow_html=True)
    with c3: st.markdown(f"**Größte Kategorie**<br><small>{kpis.get('Größte Kategorie','-')}</small>", unsafe_allow_html=True)
    with c4: st.markdown(f"**Größter Empfänger**<br><small>{kpis.get('Größter Empfänger','-')}</small>", unsafe_allow_html=True)
    st.markdown("---")
    make_charts(filtered_df)
    st.markdown("---")
    detail_analysis(filtered_df)
    st.markdown("---")
    with st.expander("📋 Buchungen", expanded=True):
        st.caption("Alle Buchungen gemäß aktueller Filterauswahl.")
        show_table(filtered_df, f"Alle Buchungen ({len(filtered_df)} Stück)")
    st.markdown("---")
    with st.expander("🔄 Regelmäßige Zahlungen", expanded=True):
        st.caption("Erkannte regelmäßige Zahlungen wie Fixkosten, Abos oder Beiträge.")
        st.caption("Sicherheit: Modellvertrauen in die Erkennung regelmäßiger Zahlungen (0-100%).")
        if not recurring_df.empty:
            show_table(recurring_df, f"Regelmäßige Zahlungen ({len(recurring_df)} Stück)")
        else:
            st.info("Keine regelmäßigen Zahlungen gefunden.")
    st.markdown("---")
    with st.expander("⚠ Auffällige Buchungen", expanded=True):
        st.caption("Auffällige Buchungen, die geprüft werden sollten.")
        if not anomalies_df.empty:
            show_table(anomalies_df, f"Auffällige Buchungen ({len(anomalies_df)} Stück)")
        else:
            st.info("Keine auffälligen Buchungen gefunden.")
    st.caption(f"Stand: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

if __name__ == "__main__":
    main()
