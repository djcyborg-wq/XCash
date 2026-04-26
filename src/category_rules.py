"""Konfigurierbare Keyword-Regeln für die Transaktions-Kategorisierung.

Dieses Modul definiert Keyword-Muster zur automatischen Zuordnung von
Transaktionen zu Kategorien. Die Regeln werden in data_cleaner.py genutzt.

Struktur:
    CATEGORY_RULES = {
        'kategorie.unterkategorie': {
            'keywords': ['liste', 'von', 'woertern'],
            'match_type': 'any' | 'all',  # any=oder-Verknuepfung, all=und-Verknuepfung
            'case_sensitive': False,
        }
    }

Priorisierung: Regeln werden von oben nach unten abgearbeitet.
Treffen mehrere Regeln zu, gewinnt die Erste.
"""

import re

# Kern-Kategorien mit Keyword-Mustern
# ---------------------------------------------------------------------------
# Prioritaet:
# - Haendler-/Produktsignale haben Vorrang.
# - Zahlungsanbieter wie PayPal/VISA/ING sind nur Kontext.
# - Generische Anbieter sollen ueber purpose/booking_text interpretiert werden.

CATEGORY_RULES = {
    # --- EINKOMMEN --------------------------------------------------------
    'income.salary': {
        'keywords': ['gehalt', 'lohn', 'rente', 'gehaltsbezug', 'einkommen',
                     'arbeitgeber', 'sv nr'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'income.refund': {
        'keywords': ['gutschrift', 'erstattung', 'zurueckzahlung', 'bonus',
                     'cashback', 'guthaben', 'vergab'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'income.transfer': {
        'keywords': ['ueberweisung', 'dauerauftrag', 'kontenausgleich',
                     'family', 'privatueberweisung', 'geldtransfer'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'income.investment': {
        'keywords': ['dividende', 'zins', 'gewinn', 'rendite', 'ertrag',
                     'ausschuettung', 'fonds', 'anlage'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- LEBENSMITTEL / SUPERMARKT ----------------------------------------
    'groceries.supermarket': {
        'keywords': ['netto', 'aldi', 'lidl', 'rewe', 'edeka', 'kaufland',
                     'penny', 'norma', 'famila', 'marktkauf', 'nahkauf',
                     'supermarkt', 'lebensmittel', 'diskont',
                     'diska', 'markgrafen-getraenkemarkt', 'markgrafen getraenkemarkt'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'groceries.discounter': {
        'keywords': ['toom', 'obi baumarkt', 'bauhaus', 'hornbach', 'hellweg'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- RESTAURANT / CAFE / ESSEN ----------------------------------------
    'dining.restaurant': {
        'keywords': ['restaurant', 'cafe', 'café', 'gaststätte', 'lokal',
                     'kantine', 'imbiss', 'bistro', 'eiscafe', 'pizzeria', 'doenerhaus'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'dining.school_meals': {
        'keywords': ['sfz cowerk', 'cowerk', 'schulessen', 'kitaessen', 'mittagessen schule'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'dining.fast_food': {
        'keywords': ['mcdonalds', 'burger king', 'subway', 'kfc', 'domino'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'dining.bakery': {
        'keywords': ['bäckerei', 'backwaren', 'rosch', 'konditorei',
                     'baecherei', 'baeckerei', 'broetchen'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- ONLINE-SHOPPING --------------------------------------------------
    'shopping.amazon': {
        'keywords': ['amazon', 'amzn', 'prime video', 'amzn mktp'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'shopping.ebay': {
        'keywords': ['ebay', 'ebay.de', 'ebay marketplace'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'shopping.clothing': {
        'keywords': ['h&m', 'h+m', 'zara', 'c&a', 'esprit', 'tom tailor', 'gap', 'engbers',
                     'nkd', 'deichmann', 'reno', 'p + p shoes', 'p+p shoes', 'intersport', 'style', 'kik',
                     'lederwaren boehm', 'lederwaren böhm'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'personal.haircare': {
        'keywords': ['salon schnittpunkt', 'friseur', 'haarschnitt', 'hair salon'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'shopping.electronics': {
        'keywords': ['mediamarkt', 'saturn', 'cyberport', 'alternate',
                     'notebooksbilliger', 'apple', 'microsoft'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'shopping.home': {
        'keywords': ['toom', 'obi baumarkt', 'bauhaus', 'hornbach', 'roller',
                     'sonderpreis baumarkt', 'sonderpreis-baumarkt',
                     'baustoffhandel', 'haustechnik', 'ttl tapeten-teppichbodenland', 'ikea'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'shopping.drugstore': {
        'keywords': ['dm', 'rossmann', 'douglas', 'parfumerie', 'drogerie', 'tedi', 'muller handels',
                     'maec geiz', 'm.c geiz'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- VERKEHR / TANKSTELLEN --------------------------------------------
    'transport.fuel': {
        'keywords': ['aral', 'shell', 'total', 'agip', 'esso', 'stark',
                     'tanke', 'tanken', 'kraftstoff', 'tankstelle',
                     'greenline', 'star'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'transport.parking': {
        'keywords': ['parking', 'pkw', 'stellplatz', 'tiefgarage'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'transport.toll': {
        'keywords': ['maut', 'autobahn', 'vignette'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'transport.car_rental': {
        'keywords': ['sixt', 'europcar', 'hertz', 'buchbinder', 'flinkster'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'transport.public': {
        'keywords': ['regionalverkehr erzgebirge', 'bildungsticket',
                     'schuelerbildungs ticket', 'schuelerbildungsticket', 'rve',
                     'deutsche bahn', 'db', 'bahn', 'oepnv', 'busabo'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'transport.maintenance': {
        'keywords': ['kfz', 'autowerkstatt', 'werkstatt', 'herrmann exklusiv'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- WOHNEN / HAUSHALT ------------------------------------------------
    'housing.rent': {
        'keywords': ['miete', 'warmmiete', 'kaltmiete', 'nebenkosten'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'housing.utilities': {
        'keywords': ['strom', 'gas', 'wasser', 'heizung', 'energie',
                     'versorger', 'stromanbieter', 'stadtwerke', 'roeben gas', 'roeben'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'housing.internet': {
        'keywords': ['telekom', 'vodafone', 'o2', 'unitymedia', 'kabel',
                     'internet', 'mobilfunk', 'handyvertrag', 'drillisch'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'housing.taxes': {
        'keywords': ['grundsteuer', 'abfall', 'abfallwirtschaft',
                     'bundeskasse', 'steuer', 'steuern', 'hauptkasse des freistaates sachsen',
                     'grose kreisstadt aue', 'grosse kreisstadt aue'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- VERSICHERUNGEN ---------------------------------------------------
    'insurance.health': {
        'keywords': ['krankenkasse', 'gesundheitskasse', 'allianz'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'insurance.car': {
        'keywords': ['kfz-versicherung', 'autoversicherung', 'haftpflicht', 'huk', 'devk',
                     'bavariadirekt', 'bd24', 'berlin direkt'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'insurance.life': {
        'keywords': ['lebensversicherung', 'risikolebensversicherung',
                     'rentenversicherung', 'altersvorsorge', 'allianz lebensvers',
                     'deurag', 'allrecht'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- ERWEITERTE REGELN (GENERIC PROVIDER) ----------------------------
    'utilities.telecom': {
        'keywords': ['telefonica', 'o2', 'vodafone', 'telekom', 'mobilfunk', 'handy'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'health.drugstore': {
        'keywords': ['dm', 'rossmann', 'müller drogerie', 'apotheke'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'banking.transaction': {
        'keywords': ['ing', 'ing-diba', 'ing diba'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'payment.card': {
        'keywords': ['kreditkarte', 'kartenzahlung', 'kreditkartenabrechnung'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'payment.paypal': {
        'keywords': ['paypal'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'payment.provider': {
        'keywords': ['first data', 'nexi', 'sumup', 'stripe', 'adyen'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'shopping.online': {
        'keywords': ['amazon', 'ebay', 'marketplace', 'zalando'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- UNTERHALTUNG / HOBBY --------------------------------------------
    'entertainment.streaming': {
        'keywords': ['netflix', 'spotify', 'prime video', 'disney+',
                     'sky', 'waipu', 'joyn', 'ard', 'zdf'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'entertainment.gaming': {
        'keywords': ['steam', 'epic games', 'origin', 'playstation',
                     'xbox', 'nintendo', 'gaming'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'entertainment.travel': {
        'keywords': ['booking', 'expedia', 'airbnb', 'hotel', 'reise',
                     'flug', 'urlaub', 'ferien', 'color magic', 'karls tourismus', 'karls markt', 'skiarena eibenstock',
                     'freizeitbad', 'badegaerten eibenstock'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'entertainment.hobby': {
        'keywords': ['thalia', 'kino', 'kinoheld', 'museum', 'event', 'repp mediumtechnik'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- GESUNDHEIT -------------------------------------------------------
    'health.pharmacy': {
        'keywords': ['apotheke', 'dm-drogerie', 'medikament'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'health.doctor': {
        'keywords': ['arzt', 'klinik', 'praxis', 'behandlung'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- ABONNEMENTS / SOFTWARE ------------------------------------------
    'subscriptions.software': {
        'keywords': ['adobe', 'microsoft', 'github', 'cursor', 'openai',
                     'microsoft 365', 'saas'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'subscriptions.membership': {
        'keywords': ['mitgliedschaft', 'verein', 'beitrag', 'gym',
                     'fitness', 'studio', 'club'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- FINANZ / BANK ----------------------------------------------------
    'fees.bank': {
        'keywords': ['entgelt', 'gebuehr', 'spesen', 'provision',
                     'gebuehren', 'kosten'],
        'match_type': 'any',
        'case_sensitive': False,
    },
    'fees.atm': {
        'keywords': ['geldautomat', 'ec-terminal', 'barabhebung', 'atm'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- INVESTMENT -------------------------------------------------------
    'finance.investment': {
        'keywords': ['smartbroker', 'depot', 'investment', 'anlage', 'auffuellen'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- INTERNATIONAL CARD PAYMENTS -------------------------------------
    'travel.foreign_card': {
        'keywords': ['american express', 'fremdwaehrung', 'auslandseinsatz'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- PRIVATE TRANSFERS -----------------------------------------------
    'transfer.private': {
        'keywords': ['neubert', 'einzahlung', 'geschenk', 'babyphone',
                     'familie', 'privat', 'auf fuellung', 'kontenausgleich',
                     'christopher thon', 'steve herrmann', 'thi bich ngoc bui', 'andreas seidel'],
        'match_type': 'any',
        'case_sensitive': False,
    },

    # --- WASTE MANAGEMENT -------------------------------------------------
    'housing.waste': {
        'keywords': ['abfall', 'entsorgung', 'muell', 'restmuell'],
        'match_type': 'any',
        'case_sensitive': False,
    },
}


def get_special_patterns():
    """Liefert spezielle Matching-Regeln als Liste von Tupeln.

    Returns:
        Liste von (muster, kategorie) Tupeln.
    """
    return [
        ('roeben.*gas', 'housing.utilities'),
        ('paypal.*kinoheld', 'entertainment.hobby'),
        ('lastschrift.*amzn', 'shopping.amazon'),
        ('paypal.*lastschrift', 'payment.paypal'),
        ('allianz.*lebensvers', 'insurance.life'),
        ('allianz.*privatschutz', 'insurance.car'),
        ('deutsche.*bahn', 'transport.public'),
        ('vbb.*ticket', 'transport.public'),
    ]


def get_exclusion_keywords():
    """Keywords die eine Kategorie ausschließen.

    Returns:
        Dict mit Kategorien und ihren Negativ-Keywords.
    """
    return {
        'income.salary': ['abzug', 'steuer', 'vorsorge'],
    }


# Generische Zahlungsanbieter - dürfen counterparty nicht allein verwenden
GENERIC_PAYMENT_PROVIDERS = [
    'visa', 'mastercard', 'paypal', 'first data', 'nexi',
    'otto payments', 'klarna', 'stripe', 'adyen', 'sumup',
    'apple pay', 'google pay', 'ing', 'ing-diba', 'ing diba'
]


def categorize_generic_provider(text, counterparty="", purpose="", booking_text=""):
    """Kategorisiert Transaktionen mit generischen Zahlungsanbietern.
    
    Logik:
    - Kombiniere purpose + booking_text zuerst.
    - counterparty nur nachrangig verwenden.
    - Wenn Anbieter generisch ist, darf counterparty alleine NICHT die Kategorie bestimmen.
    
    Args:
        text: Kombiniertes Textfeld (purpose + booking_text)
        counterparty: Gegenpartei Name
        purpose: Verwendungszweck
        booking_text: Buchungstext
        
    Returns:
        Kategorie-String oder None wenn keine Regel passt.
    """
    if not text:
        text = ""

    # purpose + booking_text haben Vorrang vor generischem counterparty
    combined_text = " ".join(
        part for part in [purpose, booking_text] if part and str(part).strip().lower() != 'nan'
    ).strip()
    if combined_text:
        text = combined_text
    elif not text or text.strip().lower() in ['', 'nan']:
        # counterparty nur nachrangig verwenden wenn kein anderer Text vorliegt
        text = counterparty if counterparty else ""
    
    text_lower = text.lower() if text else ""
    counterparty_lower = counterparty.lower() if counterparty else ""
    # purpose/booking_text bleiben primaer (text_lower), counterparty ist Zusatzkontext
    context_text = f"{text_lower} {counterparty_lower}".strip()
    
    # === ING REGELN ===
    if 'ing' in context_text or 'ing-diba' in context_text or 'ing diba' in context_text:
        if any(kw in context_text for kw in ['depot', 'wertpapier', 'sparen', 'sparplan', 'broker']):
            return 'finance.investment'
        if any(kw in context_text for kw in ['gebühr', 'girocard', 'karte', 'kontoführung']):
            return 'fees.bank'
        return 'banking.transaction'
    
    # === VISA / MASTERCARD REGELN ===
    if 'visa' in context_text or 'mastercard' in context_text:
        # Software-Abonnements
        if any(kw in context_text for kw in ['cursor', 'openai', 'microsoft', 'google', 'adobe']):
            return 'subscriptions.software'
        # Maut/Vignette
        if any(kw in context_text for kw in ['edalnice', 'vignette']):
            return 'transport.toll'
        # Parken
        if any(kw in context_text for kw in ['easypark', 'parken']):
            return 'transport.parking'
        # Baeckerei
        if any(kw in context_text for kw in ['bakery', 'backstube']):
            return 'dining.bakery'
        # Restaurant
        if any(kw in context_text for kw in ['restoran', 'konak']):
            return 'dining.restaurant'
        # Baumarkt/Haushalt
        if any(kw in context_text for kw in ['sonderpreis baumarkt', 'baustoffhandel']):
            return 'shopping.home'
        # Getraenkemarkt / Supermarkt
        if any(kw in context_text for kw in ['getraenkemarkt', 'diska']):
            return 'groceries.supermarket'
        # Grundsteuer
        if 'grundsteuer' in context_text:
            return 'housing.taxes'
        # Reisen mit Karte (spezifische AERO-Hinweise zuerst)
        if any(kw in context_text for kw in ['prg.aero', 'aero']):
            return 'travel.foreign_card'
        # Streaming
        if any(kw in context_text for kw in ['netflix', 'spotify', 'disney', 'youtube', 'apple']):
            return 'entertainment.streaming'
        # Reisen mit Karte
        if any(kw in context_text for kw in ['hotel', 'airline', 'air', 'travel', 'prague', 'norway', 
                                            'montenegro', 'color magic', 'edalnice', 'booking', 
                                            'airbnb', 'bahn', 'db']):
            return 'travel.foreign_card'
        # Online-Shopping
        if any(kw in context_text for kw in ['amazon', 'ebay', 'shop', 'marketplace', 'zalando']):
            return 'shopping.online'
        # Tankstelle
        if any(kw in context_text for kw in ['tankstelle', 'aral', 'shell', 'star', 'total', 'greenline']):
            return 'transport.fuel'
        return 'payment.card'
    
    # === PAYPAL REGELN ===
    if 'paypal' in context_text:
        # Software
        if any(kw in context_text for kw in ['openai', 'cursor']):
            return 'subscriptions.software'
        # Online-Shopping
        if any(kw in context_text for kw in ['temu', 'aliexpress']):
            return 'shopping.online'
        # Parken
        if any(kw in context_text for kw in ['easypark', 'parken']):
            return 'transport.parking'
        # Reisen mit Karte (spezifische AERO-Hinweise zuerst)
        if any(kw in context_text for kw in ['prg.aero', 'aero']):
            return 'travel.foreign_card'
        # Maut/Vignette
        if any(kw in context_text for kw in ['edalnice', 'vignette']):
            return 'transport.toll'
        # Baeckerei
        if any(kw in context_text for kw in ['bakery', 'backstube']):
            return 'dining.bakery'
        # Restaurant
        if any(kw in context_text for kw in ['restoran', 'konak']):
            return 'dining.restaurant'
        # Baumarkt/Haushalt
        if any(kw in context_text for kw in ['sonderpreis baumarkt', 'baustoffhandel']):
            return 'shopping.home'
        # Getraenkemarkt / Supermarkt
        if any(kw in context_text for kw in ['getraenkemarkt', 'diska']):
            return 'groceries.supermarket'
        # Grundsteuer
        if 'grundsteuer' in context_text:
            return 'housing.taxes'
        # Online-Shopping
        if any(kw in context_text for kw in ['amazon', 'ebay', 'shop', 'marketplace', 'zalando']):
            return 'shopping.online'
        # Software
        if any(kw in context_text for kw in ['cursor', 'openai', 'microsoft', 'google', 'adobe']):
            return 'subscriptions.software'
        # Streaming
        if any(kw in context_text for kw in ['netflix', 'spotify', 'disney', 'youtube', 'apple']):
            return 'entertainment.streaming'
        # Kino / Freizeit
        if any(kw in context_text for kw in ['kino', 'kinoheld', 'repp mediumtechnik']):
            return 'entertainment.hobby'
        # Restaurant/Lieferando
        if any(kw in context_text for kw in ['lieferando', 'restaurant', 'pizza', 'döner', 'imbiss']):
            return 'dining.restaurant'
        # Reisen
        if any(kw in context_text for kw in ['bahn', 'db', 'booking', 'hotel', 'airbnb', 'airline']):
            return 'entertainment.travel'
        return 'payment.paypal'
    
    # === FIRST DATA / NEXI / SUMUP / STRIPE / ADYEN REGELN ===
    generic_providers = ['first data', 'nexi', 'sumup', 'stripe', 'adyen']
    is_generic_provider = any(p in context_text for p in generic_providers)
    
    if is_generic_provider:
        # First Data: Verwendungszweck enthaelt oft den eigentlichen Haendler/Reisekontext.
        if 'first data' in context_text:
            if any(kw in context_text for kw in ['kaufumsatz', 'oslo', '/no/', '/me/', 'montenegro', 'norway', 'color magic']):
                return 'travel.foreign_card'
        # Software
        if any(kw in context_text for kw in ['openai', 'cursor']):
            return 'subscriptions.software'
        # Online-Shopping
        if any(kw in context_text for kw in ['temu', 'aliexpress']):
            return 'shopping.online'
        # Parken
        if any(kw in context_text for kw in ['easypark', 'parken']):
            return 'transport.parking'
        # Reisen mit Karte (spezifische AERO-Hinweise zuerst)
        if any(kw in context_text for kw in ['prg.aero', 'aero']):
            return 'travel.foreign_card'
        # Maut/Vignette
        if any(kw in context_text for kw in ['edalnice', 'vignette']):
            return 'transport.toll'
        # Bakery
        if any(kw in context_text for kw in ['bakery', 'backstube']):
            return 'dining.bakery'
        if any(kw in context_text for kw in ['bäckerei', 'backwaren', 'rosch', 'konditorei']):
            return 'dining.bakery'
        # Restaurant
        if any(kw in context_text for kw in ['restoran', 'konak']):
            return 'dining.restaurant'
        if any(kw in context_text for kw in ['restaurant', 'imbiss', 'cafe', 'café', 'pizza', 'döner']):
            return 'dining.restaurant'
        # Baumarkt/Haushalt
        if any(kw in context_text for kw in ['sonderpreis baumarkt', 'baustoffhandel']):
            return 'shopping.home'
        # Getraenkemarkt / Supermarkt
        if any(kw in context_text for kw in ['getraenkemarkt', 'diska']):
            return 'groceries.supermarket'
        # Grundsteuer
        if any(kw in context_text for kw in ['grundsteuer', 'grundsteue r']):
            return 'housing.taxes'
        # Tankstelle
        if any(kw in context_text for kw in ['tankstelle', 'aral', 'shell', 'star', 'total', 'greenline']):
            return 'transport.fuel'
        # Apotheke/Drogerie
        if any(kw in context_text for kw in ['apotheke', 'dm', 'rossmann']):
            return 'health.drugstore'
        return 'payment.provider'
    
    return None


def normalize_text(text):
    """Bereinigt Text für die Kategorisierung.

    Args:
        text: Eingabetext (kann None sein)

    Returns:
        Bereinigter Text in Kleinbuchstaben.
    """
    if not text or not isinstance(text, str):
        return ''
    t = text.lower()
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    import re
    return t
