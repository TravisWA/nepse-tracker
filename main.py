"""
NEPSE Portfolio Tracker v2.0
Personal Portfolio Management App

Features:
- Portfolio tracking with WACC
- Manual price entry (offline capable)
- Auto-fetch from 3rd party sources only
- NEPSE Index tracking
- Watchlist
- All SEBON charge calculations
- CGT calculations (7.5% / 10%)
- Ethical rate limiting

Data Sources (3rd party, public):
- ShareSansar (sharesansar.com)
- NEPSE Alpha (nepsealpha.com)
- MeroLagani (merolagani.com)

DISCLAIMER:
Personal use only. Verify prices from
official sources before making decisions.
"""

import os
import sqlite3
import datetime
import threading
import re
import time

os.environ['KIVY_NO_CONSOLELOG'] = '1'

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.screenmanager import (
    ScreenManager, Screen, SlideTransition
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.graphics import (
    Color, Rectangle, RoundedRectangle
)

# ══════════════════════════════
# ETHICAL SETTINGS
# ══════════════════════════════
FETCH_DELAY_SECONDS = 3.0
AUTO_REFRESH_MINUTES = 10
MIN_MANUAL_REFRESH_SECS = 60
MARKET_ONLY_AUTO = True

# ══════════════════════════════
# COLORS
# ══════════════════════════════
BG     = [0.05, 0.07, 0.09, 1]
CARD   = [0.09, 0.10, 0.13, 1]
CARD2  = [0.13, 0.15, 0.18, 1]
TEXT   = [0.90, 0.93, 0.95, 1]
DIM    = [0.55, 0.58, 0.62, 1]
GREEN  = [0.25, 0.73, 0.31, 1]
RED    = [0.97, 0.32, 0.29, 1]
YELLOW = [0.83, 0.66, 0.13, 1]
BLUE   = [0.35, 0.65, 1.00, 1]
ORANGE = [0.86, 0.43, 0.16, 1]
PURPLE = [0.74, 0.55, 1.00, 1]
BLACK  = [0.04, 0.04, 0.05, 1]
WHITE  = [1.00, 1.00, 1.00, 1]
CYAN   = [0.40, 0.85, 0.90, 1]


# ══════════════════════════════
# CHARGE CALCULATOR
# ══════════════════════════════
class Calc:
    SLABS = [
        (0,           2500,         0.0040),
        (2500.01,     50000,        0.0037),
        (50000.01,    500000,       0.0034),
        (500000.01,   2000000,      0.0030),
        (2000000.01,  10000000,     0.0027),
        (10000000.01, float('inf'), 0.0024),
    ]
    SEBON   = 0.00015
    DP      = 25.0
    CM      = 0.002
    MIN_BR  = 10.0
    CGT_S   = 0.075
    CGT_L   = 0.10
    DIV_TAX = 0.05

    @classmethod
    def broker(cls, amt):
        rate = cls.SLABS[-1][2]
        for lo, hi, r in cls.SLABS:
            if lo <= amt <= hi:
                rate = r
                break
        return round(max(cls.MIN_BR,
                         amt * rate), 2)

    @classmethod
    def buy(cls, qty, price):
        g  = round(qty * price, 2)
        br = cls.broker(g)
        se = round(g * cls.SEBON, 2)
        dp = cls.DP
        cm = round(g * cls.CM, 2)
        tc = round(br + se + dp + cm, 2)
        nt = round(g + tc, 2)
        return {
            'gross': g, 'broker': br,
            'sebon': se, 'dp': dp,
            'cm': cm, 'charges': tc,
            'net': nt,
            'wacc': round(nt / qty, 2)
        }

    @classmethod
    def sell(cls, qty, price):
        g  = round(qty * price, 2)
        br = cls.broker(g)
        se = round(g * cls.SEBON, 2)
        dp = cls.DP
        tc = round(br + se + dp, 2)
        nt = round(g - tc, 2)
        return {
            'gross': g, 'broker': br,
            'sebon': se, 'dp': dp,
            'cm': 0, 'charges': tc,
            'net': nt
        }

    @classmethod
    def cgt(cls, profit, buy_date_str):
        if profit <= 0:
            return 0, 'No Tax'
        try:
            bd = datetime.datetime.strptime(
                buy_date_str,
                '%Y-%m-%d').date()
            days = (datetime.date.today()
                    - bd).days
        except Exception:
            days = 0
        if days <= 365:
            return (
                round(profit * cls.CGT_S, 2),
                f'Short 7.5% ({days}d)'
            )
        return (
            round(profit * cls.CGT_L, 2),
            f'Long 10% ({days}d)'
        )

    @classmethod
    def target(cls, wacc, qty,
               buy_date, pct):
        cost = wacc * qty
        want = cost * pct / 100
        try:
            bd   = datetime.datetime.strptime(
                buy_date, '%Y-%m-%d').date()
            days = (datetime.date.today()
                    - bd).days
        except Exception:
            days = 0
        cr = (cls.CGT_S if days <= 365
              else cls.CGT_L)
        sv = cost + want
        for _ in range(20):
            sc = cls.sell(qty, sv / qty)
            gp = sv - sc['charges'] - cost
            ct = gp * cr if gp > 0 else 0
            nv = (cost + want
                  + sc['charges'] + ct)
            if abs(nv - sv) < 0.01:
                break
            sv = nv
        return round(sv / qty, 2)

    @classmethod
    def breakeven(cls, wacc, qty):
        cost = wacc * qty
        p    = wacc
        for _ in range(20):
            sc  = cls.sell(qty, p)
            np_ = ((cost + sc['charges'])
                   / qty)
            if abs(np_ - p) < 0.01:
                break
            p = np_
        return round(p, 2)

    @classmethod
    def is_open(cls):
        now = datetime.datetime.now()
        if now.weekday() > 4:
            return False
        op = now.replace(
            hour=11, minute=0,
            second=0, microsecond=0)
        cl = now.replace(
            hour=15, minute=0,
            second=0, microsecond=0)
        return op <= now <= cl

    @classmethod
    def market_status(cls):
        now = datetime.datetime.now()
        if cls.is_open():
            cl  = now.replace(hour=15,
                               minute=0)
            rem = int(
                (cl - now).total_seconds()
                / 60)
            return f'OPEN {rem}min'
        days = ['Mon','Tue','Wed',
                'Thu','Fri','Sat','Sun']
        return f'CLOSED {days[now.weekday()]}'


# ══════════════════════════════
# DATABASE
# ══════════════════════════════
class DB:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        try:
            from kivy.app import App as KApp
            a = KApp.get_running_app()
            p = os.path.join(
                a.user_data_dir, 'nepse.db')
        except Exception:
            p = 'nepse.db'

        self.path = p
        self.conn = sqlite3.connect(
            p, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS
            transactions (
                id INTEGER PRIMARY KEY
                   AUTOINCREMENT,
                trans_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                company_name TEXT DEFAULT '',
                sector TEXT DEFAULT '',
                trans_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price_per_share REAL NOT NULL,
                gross_amount REAL DEFAULT 0,
                broker_commission REAL DEFAULT 0,
                sebon_fee REAL DEFAULT 0,
                dp_charge REAL DEFAULT 0,
                capital_market_fee
                    REAL DEFAULT 0,
                total_charges REAL DEFAULT 0,
                net_amount REAL NOT NULL,
                broker_name TEXT DEFAULT '',
                notes TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS
            prices (
                symbol TEXT PRIMARY KEY,
                price REAL DEFAULT 0,
                prev_close REAL DEFAULT 0,
                day_high REAL DEFAULT 0,
                day_low REAL DEFAULT 0,
                volume INTEGER DEFAULT 0,
                updated TEXT,
                source TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS
            watchlist (
                symbol TEXT PRIMARY KEY,
                company TEXT DEFAULT '',
                target_buy REAL DEFAULT 0,
                target_sell REAL DEFAULT 0,
                notes TEXT DEFAULT '',
                added_date TEXT
            );

            CREATE TABLE IF NOT EXISTS
            nepse_index (
                id INTEGER PRIMARY KEY
                   AUTOINCREMENT,
                date TEXT,
                index_value REAL DEFAULT 0,
                change_points REAL DEFAULT 0,
                change_percent REAL DEFAULT 0,
                total_volume INTEGER DEFAULT 0,
                total_turnover REAL DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                updated TEXT
            );

            CREATE TABLE IF NOT EXISTS
            app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        ''')
        defaults = [
            ('target1', '10'),
            ('target2', '20'),
            ('target3', '30'),
            ('last_manual_refresh', '0'),
            ('auto_refresh_enabled', 'yes'),
        ]
        for k, v in defaults:
            self.conn.execute(
                '''INSERT OR IGNORE INTO
                   app_settings(key,value)
                   VALUES(?,?)''', (k, v))
        self.conn.commit()

    def run(self, sql, p=()):
        c = self.conn.execute(sql, p)
        self.conn.commit()
        return c

    def all(self, sql, p=()):
        return self.conn.execute(
            sql, p).fetchall()

    def one(self, sql, p=()):
        return self.conn.execute(
            sql, p).fetchone()

    def save_price(self, sym, data,
                   source=''):
        self.run('''
            INSERT OR REPLACE INTO prices
            (symbol,price,prev_close,
             day_high,day_low,volume,
             updated,source)
            VALUES(?,?,?,?,?,?,?,?)
        ''', (
            sym,
            data.get('price', 0),
            data.get('prev', 0),
            data.get('high', 0),
            data.get('low', 0),
            data.get('vol', 0),
            str(datetime.datetime.now()),
            source
        ))

    def save_index(self, data):
        self.run('''
            INSERT INTO nepse_index
            (date, index_value,
             change_points, change_percent,
             total_volume, total_turnover,
             total_trades, updated)
            VALUES(?,?,?,?,?,?,?,?)
        ''', (
            str(datetime.date.today()),
            data.get('index', 0),
            data.get('change', 0),
            data.get('change_pct', 0),
            data.get('volume', 0),
            data.get('turnover', 0),
            data.get('trades', 0),
            str(datetime.datetime.now())
        ))

    def get_latest_index(self):
        return self.one(
            'SELECT * FROM nepse_index'
            ' ORDER BY id DESC LIMIT 1')

    def setting(self, key, default=''):
        r = self.one(
            'SELECT value FROM app_settings'
            ' WHERE key=?', (key,))
        return r['value'] if r else default

    def set_setting(self, key, val):
        self.run(
            '''INSERT OR REPLACE INTO
               app_settings(key,value)
               VALUES(?,?)''',
            (key, str(val)))


# ══════════════════════════════
# THIRD-PARTY DATA FETCHER
# 
# Sources (public):
# 1. ShareSansar
# 2. NEPSE Alpha  
# 3. MeroLagani
# 
# NO direct NEPSE fetching
# All ethical rate limiting
# ══════════════════════════════
class Fetcher:
    UA = {
        'User-Agent': (
            'Mozilla/5.0 (Linux; Android 10)'
            ' AppleWebKit/537.36'
        ),
        'Accept': 'text/html,application/json',
    }

    _last_fetch_time = 0

    @classmethod
    def _wait_delay(cls):
        elapsed = time.time() - cls._last_fetch_time
        if elapsed < FETCH_DELAY_SECONDS:
            wait = FETCH_DELAY_SECONDS - elapsed
            time.sleep(wait)
        cls._last_fetch_time = time.time()

    @classmethod
    def fetch_price(cls, symbol):
        """Try 3rd party sources only"""
        cls._wait_delay()

        # Source 1: ShareSansar
        result = cls._sharesansar(symbol)
        if result:
            result['source'] = 'ShareSansar'
            return result

        time.sleep(2)

        # Source 2: NEPSE Alpha
        result = cls._nepsealpha(symbol)
        if result:
            result['source'] = 'NEPSE Alpha'
            return result

        time.sleep(2)

        # Source 3: MeroLagani (backup)
        result = cls._merolagani(symbol)
        if result:
            result['source'] = 'MeroLagani'
            return result

        return None

    @classmethod
    def _sharesansar(cls, symbol):
        """ShareSansar public data"""
        try:
            import requests
            url = (
                'https://www.sharesansar.com'
                f'/company/{symbol.lower()}'
            )
            r = requests.get(
                url, headers=cls.UA,
                timeout=15, verify=True)

            if r.status_code == 200:
                text = r.text

                # Multiple patterns to try
                patterns = {
                    'price': [
                        r'Last\s+Traded\s+Price'
                        r'[^0-9]*?([\d,]+\.\d+)',
                        r'ltp["\s:]+([\d,]+\.\d+)',
                    ],
                    'prev': [
                        r'Previous\s+Close'
                        r'[^0-9]*?([\d,]+\.\d+)',
                    ],
                    'high': [
                        r'Day.?s?\s+High'
                        r'[^0-9]*?([\d,]+\.\d+)',
                        r'High\s+Price'
                        r'[^0-9]*?([\d,]+\.\d+)',
                    ],
                    'low': [
                        r'Day.?s?\s+Low'
                        r'[^0-9]*?([\d,]+\.\d+)',
                        r'Low\s+Price'
                        r'[^0-9]*?([\d,]+\.\d+)',
                    ],
                    'vol': [
                        r'Volume'
                        r'[^0-9]*?([\d,]+)',
                        r'Total\s+Traded\s+Qty'
                        r'[^0-9]*?([\d,]+)',
                    ],
                }

                def find(patterns_list):
                    for p in patterns_list:
                        m = re.search(
                            p, text,
                            re.IGNORECASE)
                        if m:
                            try:
                                v = m.group(1)\
                                    .replace(
                                        ',', '')
                                return float(v)
                            except Exception:
                                continue
                    return 0

                price = find(patterns['price'])
                if price > 0:
                    return {
                        'price': price,
                        'prev': find(
                            patterns['prev']),
                        'high': find(
                            patterns['high']),
                        'low': find(
                            patterns['low']),
                        'vol': int(find(
                            patterns['vol'])),
                    }
        except Exception:
            pass
        return None

    @classmethod
    def _nepsealpha(cls, symbol):
        """NEPSE Alpha public API"""
        try:
            import requests
            # Get chart data
            end_ts = int(time.time())
            start_ts = end_ts - (7 * 86400)

            url = (
                'https://www.nepsealpha.com'
                '/trading/1/history'
                f'?symbol={symbol.upper()}'
                '&resolution=1D'
                f'&from={start_ts}'
                f'&to={end_ts}'
            )
            r = requests.get(
                url, headers=cls.UA,
                timeout=15, verify=True)

            if r.status_code == 200:
                data = r.json()
                if data.get('s') == 'ok':
                    closes = data.get('c', [])
                    highs = data.get('h', [])
                    lows = data.get('l', [])
                    vols = data.get('v', [])

                    if closes:
                        current = float(
                            closes[-1])
                        prev = (
                            float(closes[-2])
                            if len(closes) > 1
                            else current)
                        return {
                            'price': current,
                            'prev': prev,
                            'high': (
                                float(highs[-1])
                                if highs
                                else current),
                            'low': (
                                float(lows[-1])
                                if lows
                                else current),
                            'vol': (
                                int(vols[-1])
                                if vols
                                else 0),
                        }
        except Exception:
            pass
        return None

    @classmethod
    def _merolagani(cls, symbol):
        """MeroLagani - backup source"""
        try:
            import requests
            url = (
                'https://merolagani.com'
                '/CompanyDetail.aspx'
                f'?symbol={symbol.upper()}'
            )
            r = requests.get(
                url, headers=cls.UA,
                timeout=15, verify=True)

            if r.status_code == 200:
                text = r.text

                def find_val(field):
                    pattern = (
                        r'id="ctl00_'
                        r'ContentPlaceHolder1_'
                        r'CompanyDetail1_lbl'
                        + field
                        + r'"[^>]*>'
                        r'([^<]+)<'
                    )
                    m = re.search(
                        pattern, text)
                    if m:
                        try:
                            return float(
                                m.group(1)
                                .strip()
                                .replace(',',''))
                        except Exception:
                            return 0
                    return 0

                p = find_val('MarketPrice')
                if p > 0:
                    return {
                        'price': p,
                        'prev': find_val(
                            'PreviousClose'),
                        'high': find_val('High'),
                        'low': find_val('Low'),
                        'vol': 0,
                    }
        except Exception:
            pass
        return None

    @classmethod
    def fetch_nepse_index(cls):
        """Fetch NEPSE index from 3rd party"""
        cls._wait_delay()

        # Try ShareSansar
        try:
            import requests
            url = (
                'https://www.sharesansar.com'
                '/live-trading'
            )
            r = requests.get(
                url, headers=cls.UA,
                timeout=15, verify=True)

            if r.status_code == 200:
                text = r.text

                # NEPSE Index
                idx_pat = (
                    r'NEPSE\s+Index'
                    r'[^0-9]*?([\d,]+\.\d+)'
                )
                idx_m = re.search(
                    idx_pat, text,
                    re.IGNORECASE)

                if idx_m:
                    idx_val = float(
                        idx_m.group(1)
                        .replace(',', ''))

                    # Change (points)
                    chg_pat = (
                        r'NEPSE.*?'
                        r'([+-]?[\d,]+\.\d+)'
                        r'\s*\('
                        r'([+-]?\d+\.\d+)%\)'
                    )
                    chg_m = re.search(
                        chg_pat, text,
                        re.DOTALL)

                    change = 0
                    change_pct = 0
                    if chg_m:
                        try:
                            change = float(
                                chg_m.group(1)
                                .replace(',',''))
                            change_pct = float(
                                chg_m.group(2))
                        except Exception:
                            pass

                    # Volume
                    vol_pat = (
                        r'Total\s+Volume'
                        r'[^0-9]*?([\d,]+)'
                    )
                    vol_m = re.search(
                        vol_pat, text,
                        re.IGNORECASE)
                    volume = 0
                    if vol_m:
                        try:
                            volume = int(
                                vol_m.group(1)
                                .replace(',',''))
                        except Exception:
                            pass

                    # Turnover
                    tur_pat = (
                        r'Total\s+Turnover'
                        r'[^0-9]*?([\d,]+\.\d+)'
                    )
                    tur_m = re.search(
                        tur_pat, text,
                        re.IGNORECASE)
                    turnover = 0
                    if tur_m:
                        try:
                            turnover = float(
                                tur_m.group(1)
                                .replace(',',''))
                        except Exception:
                            pass

                    return {
                        'index': idx_val,
                        'change': change,
                        'change_pct': change_pct,
                        'volume': volume,
                        'turnover': turnover,
                        'trades': 0,
                    }
        except Exception:
            pass

        # Fallback: NEPSE Alpha for index
        try:
            import requests
            url = (
                'https://www.nepsealpha.com'
                '/trading/1/history'
                '?symbol=NEPSE'
                '&resolution=1D'
                f'&from={int(time.time())-86400}'
                f'&to={int(time.time())}'
            )
            r = requests.get(
                url, headers=cls.UA,
                timeout=15, verify=True)

            if r.status_code == 200:
                data = r.json()
                if data.get('s') == 'ok':
                    closes = data.get('c', [])
                    vols = data.get('v', [])
                    if closes:
                        current = float(
                            closes[-1])
                        prev = (
                            float(closes[-2])
                            if len(closes) > 1
                            else current)
                        change = current - prev
                        change_pct = (
                            change / prev * 100
                            if prev else 0)
                        return {
                            'index': current,
                            'change': round(
                                change, 2),
                            'change_pct': round(
                                change_pct, 2),
                            'volume': (
                                int(vols[-1])
                                if vols else 0),
                            'turnover': 0,
                            'trades': 0,
                        }
        except Exception:
            pass

        return None

    @classmethod
    def can_manual_refresh(cls, db):
        try:
            last = float(
                db.setting(
                    'last_manual_refresh',
                    '0'))
            now = time.time()
            if now - last < MIN_MANUAL_REFRESH_SECS:
                wait = int(
                    MIN_MANUAL_REFRESH_SECS
                    - (now - last))
                return False, wait
            return True, 0
        except Exception:
            return True, 0

    @classmethod
    def mark_manual_refresh(cls, db):
        db.set_setting(
            'last_manual_refresh',
            time.time())


# ══════════════════════════════
# PORTFOLIO ENGINE
# ══════════════════════════════
class Portfolio:
    def __init__(self):
        self.db = DB.get()

    def holding(self, symbol):
        txns = self.db.all(
            'SELECT * FROM transactions'
            ' WHERE symbol=?'
            ' ORDER BY trans_date,id',
            (symbol,)
        )
        if not txns:
            return None

        buys  = [t for t in txns
                 if t['trans_type'] == 'BUY']
        sells = [t for t in txns
                 if t['trans_type'] == 'SELL']
        bq = sum(t['quantity'] for t in buys)
        sq = sum(t['quantity'] for t in sells)
        cq = bq - sq
        if cq <= 0:
            return None

        bc   = sum(t['net_amount']
                   for t in buys)
        wacc = bc / bq if bq else 0
        tc   = wacc * cq
        first = (buys[0]['trans_date']
                 if buys else
                 str(datetime.date.today()))

        try:
            bd   = datetime.datetime\
                .strptime(first,
                          '%Y-%m-%d').date()
            hold = (datetime.date.today()
                    - bd).days
        except Exception:
            hold = 0

        pc   = self.db.one(
            'SELECT * FROM prices'
            ' WHERE symbol=?', (symbol,))
        cmp_ = pc['price'] if pc else 0
        prev = pc['prev_close'] if pc else 0
        high = pc['day_high'] if pc else 0
        low_ = pc['day_low'] if pc else 0
        vol  = pc['volume'] if pc else 0
        src  = (pc['source']
                if pc and 'source' in pc.keys()
                else '')

        cv   = cq * cmp_ if cmp_ else 0
        upl  = cv - tc if cmp_ else 0
        plp  = (upl / tc * 100
                if tc and cmp_ else 0)
        dchg = cmp_ - prev if cmp_ and prev else 0
        dpct = (dchg / prev * 100
                if prev and cmp_ else 0)

        sc   = (Calc.sell(cq, cmp_)
                if cmp_ else {})
        ca, cl = (
            Calc.cgt(upl, first)
            if upl > 0
            else (0, 'No Tax')
        )
        netp = (upl
                - sc.get('charges', 0)
                - ca
                if cmp_ else 0)

        be  = Calc.breakeven(wacc, cq)
        tp1 = Calc.target(wacc,cq,first,10)
        tp2 = Calc.target(wacc,cq,first,20)
        tp3 = Calc.target(wacc,cq,first,30)

        sig, scol = self._signal(
            cmp_, wacc, be, tp1)

        return {
            'symbol':   symbol,
            'company':  (txns[0]['company_name']
                         or symbol),
            'first':    first,
            'hold':     hold,
            'cq': cq,
            'wacc': round(wacc, 2),
            'tc':   round(tc, 2),
            'cmp':  cmp_,
            'prev': prev,
            'high': high,
            'low':  low_,
            'vol':  vol,
            'src':  src,
            'dchg': round(dchg, 2),
            'dpct': round(dpct, 2),
            'cv':   round(cv, 2),
            'upl':  round(upl, 2),
            'plp':  round(plp, 2),
            'sell_ch': round(
                sc.get('charges', 0), 2),
            'cgt':  round(ca, 2),
            'cgtl': cl,
            'netp': round(netp, 2),
            'be':   be,
            'tp1':  tp1,
            'tp2':  tp2,
            'tp3':  tp3,
            'sig':  sig,
            'scol': scol,
            'bq': bq,
        }

    def _signal(self, cmp_, wacc, be, tp1):
        if not cmp_ or cmp_ == 0:
            return 'No Price', DIM
        if cmp_ >= tp1 * 1.15:
            return 'STRONG SELL', GREEN
        if cmp_ >= tp1:
            return 'SELL Target', GREEN
        if cmp_ >= be:
            return 'HOLD Profit', YELLOW
        if cmp_ >= wacc * 0.95:
            return 'Near Cost', ORANGE
        return 'LOSS', RED

    def all_holdings(self):
        syms = self.db.all(
            'SELECT DISTINCT symbol'
            ' FROM transactions'
            ' WHERE trans_type="BUY"'
            ' ORDER BY symbol'
        )
        result = []
        for s in syms:
            h = self.holding(s['symbol'])
            if h:
                result.append(h)
        return result

    def totals(self):
        hs = self.all_holdings()
        if not hs:
            return {
                'inv': 0, 'val': 0,
                'pl': 0, 'plp': 0,
                'cgt': 0, 'net': 0,
                'n': 0,
            }
        inv  = sum(h['tc']      for h in hs)
        val  = sum(h['cv']      for h in hs)
        pl   = val - inv
        cgt  = sum(h['cgt']     for h in hs)
        sc   = sum(h['sell_ch'] for h in hs)
        return {
            'inv':  round(inv, 2),
            'val':  round(val, 2),
            'pl':   round(pl, 2),
            'plp':  round(
                pl/inv*100 if inv else 0, 2),
            'cgt':  round(cgt, 2),
            'net':  round(val-cgt-sc, 2),
            'n':    len(hs),
        }


# ══════════════════════════════
# UI HELPERS
# ══════════════════════════════
def set_bg(w, color):
    with w.canvas.before:
        Color(*color)
        Rectangle(pos=w.pos, size=w.size)
    def _r(*a):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*color)
            Rectangle(pos=w.pos, size=w.size)
    w.bind(pos=_r, size=_r)


def set_card_bg(w, color=None, radius=8):
    c = color or CARD
    with w.canvas.before:
        Color(*c)
        RoundedRectangle(
            pos=w.pos, size=w.size,
            radius=[dp(radius)])
    def _r(*a):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*c)
            RoundedRectangle(
                pos=w.pos, size=w.size,
                radius=[dp(radius)])
    w.bind(pos=_r, size=_r)


def L(text, size=13, color=None,
      bold=False, halign='left',
      height=None, **kw):
    lbl = Label(
        text=text, font_size=sp(size),
        color=color or TEXT, bold=bold,
        halign=halign, **kw)
    lbl.bind(size=lambda i, v:
             setattr(i, 'text_size',
                     (v[0], None)))
    if height:
        lbl.size_hint_y = None
        lbl.height = dp(height)
    return lbl


def B(text, callback, bg=None,
      height=48, **kw):
    btn = Button(
        text=text, font_size=sp(13),
        background_normal='',
        background_color=bg or BLUE,
        color=WHITE,
        size_hint_y=None,
        height=dp(height), **kw)
    btn.bind(on_press=lambda x: callback())
    return btn


def I(hint='', text='', height=46,
      input_filter=None, **kw):
    ti = TextInput(
        hint_text=hint, text=str(text),
        multiline=False, font_size=sp(13),
        background_color=CARD2,
        foreground_color=TEXT,
        hint_text_color=DIM,
        cursor_color=BLUE,
        size_hint_y=None,
        height=dp(height),
        padding=[dp(12), dp(10)], **kw)
    if input_filter:
        ti.input_filter = input_filter
    return ti


def S(values, current=None, height=46):
    return Spinner(
        text=current or values[0],
        values=values, font_size=sp(12),
        background_normal='',
        background_color=CARD2, color=TEXT,
        size_hint_y=None,
        height=dp(height))


def show_msg(title, msg):
    content = BoxLayout(
        orientation='vertical',
        padding=dp(15), spacing=dp(10))
    set_bg(content, CARD)
    lbl = Label(
        text=msg, font_size=sp(12),
        color=TEXT, halign='left',
        size_hint_y=None)
    lbl.bind(
        size=lambda i, v:
        setattr(i, 'text_size',
                (v[0], None)),
        texture_size=lambda i, v:
        setattr(i, 'height', v[1]+dp(10)))
    ok = B('OK', lambda: None,
           bg=BLUE, height=44)
    popup = Popup(
        title=title, title_color=BLUE,
        content=content,
        size_hint=(0.88, None),
        height=dp(280),
        background='',
        background_color=CARD)
    ok.bind(on_press=popup.dismiss)
    content.add_widget(lbl)
    content.add_widget(ok)
    popup.open()


def make_nav(sm, current):
    items = [
        ('Home', 'dash'),
        ('Port', 'port'),
        ('Add',  'add'),
        ('Watch','watch'),
        ('Manual','manual'),
        ('Info', 'info'),
    ]
    nav = BoxLayout(
        orientation='horizontal',
        size_hint_y=None,
        height=dp(56), spacing=dp(1))
    set_bg(nav, BLACK)
    for label, name in items:
        bg = BLUE if name == current else CARD2
        btn = Button(
            text=label, font_size=sp(10),
            background_normal='',
            background_color=bg,
            color=WHITE)
        def _go(i, n=name):
            sm.transition = SlideTransition(
                direction='left')
            sm.current = n
        btn.bind(on_press=_go)
        nav.add_widget(btn)
    return nav


# ══════════════════════════════
# DASHBOARD SCREEN
# with NEPSE INDEX
# ══════════════════════════════
class DashScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='dash', **kw)
        self.port = Portfolio()
        self._built = False
        self._is_fetching = False

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True
        self._update()

    def _build(self):
        root = BoxLayout(orientation='vertical')
        set_bg(root, BG)

        # Header
        hdr = BoxLayout(
            size_hint_y=None, height=dp(52),
            padding=[dp(12), dp(8)])
        set_bg(hdr, CARD)
        self.title_lbl = L(
            'NEPSE Tracker', size=16,
            bold=True, color=BLUE, height=36)
        self.mkt_lbl = L(
            Calc.market_status(),
            size=10, color=GREEN,
            height=36, halign='right')
        hdr.add_widget(self.title_lbl)
        hdr.add_widget(self.mkt_lbl)

        # NEPSE INDEX CARD
        idx_card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(80),
            padding=dp(10),
            spacing=dp(2))
        set_card_bg(idx_card, CARD)

        idx_hdr = BoxLayout(
            size_hint_y=None,
            height=dp(20))
        idx_hdr.add_widget(L(
            'NEPSE INDEX', size=10,
            color=CYAN, bold=True))
        self.idx_time = L(
            '', size=8, color=DIM,
            halign='right')
        idx_hdr.add_widget(self.idx_time)
        idx_card.add_widget(idx_hdr)

        idx_row = BoxLayout(
            size_hint_y=None,
            height=dp(28))
        self.idx_val = L(
            '---', size=18, bold=True,
            color=CYAN,
            size_hint_x=0.4)
        self.idx_chg = L(
            '---', size=13, bold=True,
            color=DIM,
            size_hint_x=0.35,
            halign='center')
        self.idx_vol = L(
            '---', size=10,
            color=DIM,
            size_hint_x=0.25,
            halign='right')
        idx_row.add_widget(self.idx_val)
        idx_row.add_widget(self.idx_chg)
        idx_row.add_widget(self.idx_vol)
        idx_card.add_widget(idx_row)

        self.idx_info = L(
            'Tap Refresh to load NEPSE data',
            size=9, color=DIM, height=15)
        idx_card.add_widget(self.idx_info)

        # Refresh row
        ref_row = BoxLayout(
            size_hint_y=None, height=dp(50),
            padding=[dp(8), dp(4)],
            spacing=dp(8))
        set_bg(ref_row, BG)
        ref_btn = B('Refresh All',
                    self._refresh,
                    bg=GREEN, height=42)
        self.upd_lbl = L(
            'Auto: 10 min',
            size=9,
            color=DIM, height=42,
            halign='right')
        ref_row.add_widget(ref_btn)
        ref_row.add_widget(self.upd_lbl)

        # Portfolio summary cards
        cards = GridLayout(
            cols=2, size_hint_y=None,
            height=dp(160), spacing=dp(5),
            padding=[dp(8), dp(4)])
        set_bg(cards, BG)
        self.card_lbl = {}
        for key, title, col in [
            ('inv', 'Invested', BLUE),
            ('val', 'Value', PURPLE),
            ('pl',  'P/L', GREEN),
            ('net', 'Net', GREEN),
        ]:
            card = BoxLayout(
                orientation='vertical',
                padding=dp(8),
                size_hint_y=None,
                height=dp(70))
            set_card_bg(card, CARD)
            tl = L(title, size=9,
                   color=DIM, height=20)
            vl = L('Rs 0', size=13,
                   bold=True, color=col,
                   height=25)
            card.add_widget(tl)
            card.add_widget(vl)
            self.card_lbl[key] = vl
            cards.add_widget(card)

        self.stats_lbl = L(
            'Loading...', size=10,
            color=DIM, height=24)

        # Holdings list
        sv = ScrollView(do_scroll_x=False)
        self.holdings_box = BoxLayout(
            orientation='vertical',
            size_hint_y=None, spacing=dp(4),
            padding=[dp(6), dp(4)])
        self.holdings_box.bind(
            minimum_height=
            self.holdings_box.setter('height'))
        sv.add_widget(self.holdings_box)

        nav = make_nav(self.manager, 'dash')

        root.add_widget(hdr)
        root.add_widget(idx_card)
        root.add_widget(ref_row)
        root.add_widget(cards)
        root.add_widget(self.stats_lbl)
        root.add_widget(sv)
        root.add_widget(nav)
        self.add_widget(root)

    def _update(self):
        t = self.port.totals()
        hs = self.port.all_holdings()
        self.mkt_lbl.text = (
            Calc.market_status())

        # NEPSE Index
        db = DB.get()
        idx = db.get_latest_index()
        if idx:
            self.idx_val.text = (
                f"{idx['index_value']:,.2f}")
            chg = idx['change_points']
            pct = idx['change_percent']
            arr = '▲' if chg >= 0 else '▼'
            col = GREEN if chg >= 0 else RED
            self.idx_chg.text = (
                f"{arr} {abs(chg):.2f}\n"
                f"({pct:+.2f}%)")
            self.idx_chg.color = col
            vol = idx['total_volume'] or 0
            if vol > 0:
                self.idx_vol.text = (
                    f"Vol: {vol/1e6:.1f}M")
            else:
                self.idx_vol.text = ''
            try:
                dt = idx['updated'][:16]
                self.idx_time.text = dt
                self.idx_info.text = (
                    f"Source: 3rd party APIs")
            except Exception:
                pass
        else:
            self.idx_val.text = '---'
            self.idx_chg.text = '---'
            self.idx_vol.text = ''

        # Portfolio cards
        self.card_lbl['inv'].text = (
            f"Rs {t['inv']:,.0f}")
        self.card_lbl['val'].text = (
            f"Rs {t['val']:,.0f}")
        self.card_lbl['pl'].text = (
            f"Rs {t['pl']:,.0f}\n"
            f"({t['plp']:.1f}%)")
        self.card_lbl['pl'].color = (
            GREEN if t['pl'] >= 0 else RED)
        self.card_lbl['net'].text = (
            f"Rs {t['net']:,.0f}")
        self.stats_lbl.text = (
            f"  {t['n']} stocks held")

        # Holdings
        self.holdings_box.clear_widgets()
        for h in hs:
            row = BoxLayout(
                size_hint_y=None,
                height=dp(65),
                padding=dp(6),
                spacing=dp(4))
            set_card_bg(row, CARD, 6)
            pl_c = (GREEN if h['plp'] >= 0
                    else RED)
            cmp_s = (f"Rs {h['cmp']:,.0f}"
                     if h['cmp'] else 'N/A')
            dchg_s = ''
            if h['cmp'] and h['dchg']:
                arr = ('▲' if h['dchg'] >= 0
                       else '▼')
                dchg_s = (
                    f"{arr}{abs(h['dchg']):.1f}")

            row.add_widget(L(
                f"[b]{h['symbol']}[/b]\n"
                f"{h['cq']}sh",
                size=11, markup=True,
                size_hint_x=0.22))
            row.add_widget(L(
                f"{cmp_s}\n{dchg_s}",
                size=10, color=BLUE,
                size_hint_x=0.22,
                halign='center'))
            row.add_widget(L(
                (f"{h['plp']:.1f}%"
                 if h['cmp'] else 'N/A'),
                size=11, color=pl_c,
                size_hint_x=0.18,
                halign='center'))
            vol_s = (f"V:{h['vol']/1000:.0f}K"
                     if h['vol'] else '')
            row.add_widget(L(
                f"{h['sig']}\n{vol_s}",
                size=9,
                color=h['scol'],
                size_hint_x=0.38,
                halign='center'))
            self.holdings_box.add_widget(row)

    def _refresh(self):
        if self._is_fetching:
            show_msg(
                'Please Wait',
                'Already fetching!')
            return

        db = DB.get()
        can_refresh, wait = (
            Fetcher.can_manual_refresh(db))

        if not can_refresh:
            show_msg(
                'Please Wait',
                f'Rate limit protection.\n'
                f'Wait {wait} seconds.')
            return

        self._is_fetching = True
        Fetcher.mark_manual_refresh(db)
        self.upd_lbl.text = 'Fetching...'

        def fetch():
            try:
                # Fetch NEPSE Index first
                idx = Fetcher.fetch_nepse_index()
                if idx:
                    db.save_index(idx)

                # Then stock prices
                syms = db.all(
                    'SELECT DISTINCT symbol'
                    ' FROM transactions'
                    ' WHERE trans_type="BUY"')
                for s in syms:
                    d = Fetcher.fetch_price(
                        s['symbol'])
                    if d:
                        db.save_price(
                            s['symbol'], d,
                            d.get('source',''))

                # Watchlist prices too
                wl = db.all(
                    'SELECT symbol'
                    ' FROM watchlist')
                for w in wl:
                    d = Fetcher.fetch_price(
                        w['symbol'])
                    if d:
                        db.save_price(
                            w['symbol'], d,
                            d.get('source',''))

                Clock.schedule_once(
                    lambda dt: self._done(), 0)
            finally:
                self._is_fetching = False

        threading.Thread(
            target=fetch, daemon=True).start()

    @mainthread
    def _done(self):
        now = datetime.datetime.now()
        self.upd_lbl.text = (
            f"Updated "
            f"{now.strftime('%H:%M')}")
        self._update()


# ══════════════════════════════
# PORTFOLIO DETAIL SCREEN
# ══════════════════════════════
class PortScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='port', **kw)
        self.port = Portfolio()
        self._built = False

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True
        self._update()

    def _build(self):
        root = BoxLayout(orientation='vertical')
        set_bg(root, BG)
        hdr = L('Portfolio Details', size=16,
                bold=True, color=BLUE,
                height=46, halign='center')
        sv = ScrollView(do_scroll_x=False)
        self.dbox = BoxLayout(
            orientation='vertical',
            size_hint_y=None, spacing=dp(8),
            padding=dp(8))
        self.dbox.bind(
            minimum_height=
            self.dbox.setter('height'))
        sv.add_widget(self.dbox)
        nav = make_nav(self.manager, 'port')
        root.add_widget(hdr)
        root.add_widget(sv)
        root.add_widget(nav)
        self.add_widget(root)

    def _update(self):
        self.dbox.clear_widgets()
        hs = self.port.all_holdings()
        if not hs:
            self.dbox.add_widget(L(
                '  No stocks yet.\n'
                '  Go to Add tab.',
                size=13, color=DIM,
                height=80))
            return
        for h in hs:
            pl_c = (GREEN if h['upl'] >= 0
                    else RED)
            card = BoxLayout(
                orientation='vertical',
                padding=dp(12),
                size_hint_y=None)
            set_card_bg(card, CARD)
            cmp_s = (f"Rs {h['cmp']:,.2f}"
                     if h['cmp']
                     else 'No price')

            vol_s = ''
            if h['vol']:
                vol_s = (
                    f"\nVolume: {h['vol']:,}")
            src_s = ''
            if h['src']:
                src_s = (
                    f"\nSource: {h['src']}")

            txt = (
                f"[b]{h['symbol']}[/b]"
                f" - {h['company']}\n"
                f"{'-'*32}\n"
                f"Qty: {h['cq']}"
                f"  WACC: Rs {h['wacc']:,.2f}\n"
                f"CMP: {cmp_s}\n"
                f"Day: Rs {h['dchg']:+,.2f}"
                f" ({h['dpct']:+.2f}%)\n"
                f"High: Rs {h['high']:,.2f}"
                f"  Low: Rs {h['low']:,.2f}"
                f"{vol_s}"
                f"{src_s}\n\n"
                f"Cost: Rs {h['tc']:,.2f}\n"
                f"Value: Rs {h['cv']:,.2f}\n"
                f"P/L: Rs {h['upl']:,.2f}"
                f" ({h['plp']:.2f}%)\n\n"
                f"[b]If Sold:[/b]\n"
                f"Charges: Rs {h['sell_ch']:,.2f}\n"
                f"CGT: Rs {h['cgt']:,.2f}\n"
                f"Net: Rs {h['netp']:,.2f}\n\n"
                f"[b]Targets:[/b]\n"
                f"BE: Rs {h['be']:,.2f}\n"
                f"10%: Rs {h['tp1']:,.2f}\n"
                f"20%: Rs {h['tp2']:,.2f}\n"
                f"30%: Rs {h['tp3']:,.2f}\n"
                f"\n[b]{h['sig']}[/b]"
            )
            lbl = Label(
                text=txt, font_size=sp(11),
                markup=True, halign='left',
                color=pl_c,
                size_hint_y=None)
            lbl.bind(
                size=lambda i, v:
                setattr(i, 'text_size',
                        (v[0], None)),
                texture_size=lambda i, v:
                setattr(i, 'height',
                        v[1] + dp(10)))
            card.add_widget(lbl)
            card.bind(
                minimum_height=
                card.setter('height'))
            self.dbox.add_widget(card)


# ══════════════════════════════
# ADD TRANSACTION SCREEN
# ══════════════════════════════
class AddScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='add', **kw)
        self.db = DB.get()
        self.port = Portfolio()
        self._built = False

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True
        self.f_date.text = (
            str(datetime.date.today()))

    def _build(self):
        root = BoxLayout(orientation='vertical')
        set_bg(root, BG)
        hdr = L('Add Transaction', size=15,
                bold=True, color=BLUE,
                height=46, halign='center')
        sv = ScrollView(do_scroll_x=False)
        form = GridLayout(
            cols=1, spacing=dp(6),
            padding=dp(10), size_hint_y=None)
        form.bind(minimum_height=
                  form.setter('height'))

        def field(label, widget):
            b = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=dp(76),
                spacing=dp(2))
            b.add_widget(L(
                label, size=11,
                color=DIM, height=22))
            b.add_widget(widget)
            return b

        self.f_date  = I('YYYY-MM-DD',
            str(datetime.date.today()))
        self.f_sym   = I('e.g. NABIL')
        self.f_comp  = I('Company Name')
        self.f_qty   = I('Shares',
            input_filter='int')
        self.f_price = I('Price Rs',
            input_filter='float')
        self.f_brok  = I('Broker')
        self.f_type  = S(['BUY','SELL'])

        form.add_widget(field(
            'Date', self.f_date))
        form.add_widget(field(
            'Symbol', self.f_sym))
        form.add_widget(field(
            'Company', self.f_comp))
        form.add_widget(field(
            'Type', self.f_type))
        form.add_widget(field(
            'Quantity', self.f_qty))
        form.add_widget(field(
            'Price/Share', self.f_price))
        form.add_widget(field(
            'Broker', self.f_brok))

        self.preview = Label(
            text='Tap Calculate',
            font_size=sp(11),
            color=GREEN, markup=True,
            halign='left',
            size_hint_y=None,
            height=dp(10))
        self.preview.bind(
            size=lambda i, v:
            setattr(i, 'text_size',
                    (v[0], None)),
            texture_size=lambda i, v:
            setattr(i, 'height',
                    v[1] + dp(15)))
        form.add_widget(self.preview)

        btns = BoxLayout(
            size_hint_y=None,
            height=dp(50), spacing=dp(8))
        btns.add_widget(B(
            'Calc', self._calc,
            bg=YELLOW, height=44))
        btns.add_widget(B(
            'Save', self._save,
            bg=GREEN, height=44))
        btns.add_widget(B(
            'Clear', self._clear,
            bg=DIM, height=44))
        form.add_widget(btns)
        sv.add_widget(form)

        nav = make_nav(self.manager, 'add')
        root.add_widget(hdr)
        root.add_widget(sv)
        root.add_widget(nav)
        self.add_widget(root)

    def _calc(self):
        try:
            qty = int(self.f_qty.text or '0')
            price = float(
                self.f_price.text or '0')
            ttype = self.f_type.text
            if qty <= 0 or price <= 0:
                self.preview.text = (
                    'Enter Qty and Price!')
                return
            if ttype == 'BUY':
                c = Calc.buy(qty, price)
                self.preview.text = (
                    f"[b]BUY CHARGES[/b]\n"
                    f"Gross: Rs {c['gross']:,.2f}\n"
                    f"Broker: Rs {c['broker']:,.2f}\n"
                    f"SEBON: Rs {c['sebon']:,.2f}\n"
                    f"DP: Rs {c['dp']:.2f}\n"
                    f"CM Fee: Rs {c['cm']:,.2f}\n"
                    f"Total: Rs {c['charges']:,.2f}\n"
                    f"[b]NET: Rs {c['net']:,.2f}[/b]\n"
                    f"[b]WACC: Rs {c['wacc']:,.2f}[/b]"
                )
            else:
                c = Calc.sell(qty, price)
                self.preview.text = (
                    f"[b]SELL CHARGES[/b]\n"
                    f"Gross: Rs {c['gross']:,.2f}\n"
                    f"Broker: Rs {c['broker']:,.2f}\n"
                    f"SEBON: Rs {c['sebon']:,.2f}\n"
                    f"DP: Rs {c['dp']:.2f}\n"
                    f"Total: Rs {c['charges']:,.2f}\n"
                    f"[b]NET: Rs {c['net']:,.2f}[/b]"
                )
        except Exception:
            self.preview.text = (
                'Check inputs!')

    def _save(self):
        try:
            date = self.f_date.text.strip()
            sym = (self.f_sym.text
                   .upper().strip())
            comp = self.f_comp.text.strip()
            ttype = self.f_type.text
            qty = int(self.f_qty.text or '0')
            price = float(
                self.f_price.text or '0')
            brok = self.f_brok.text.strip()

            if not sym:
                show_msg('Error',
                         'Symbol needed!')
                return
            if qty <= 0 or price <= 0:
                show_msg('Error',
                         'Invalid Qty/Price')
                return

            if ttype == 'BUY':
                c = Calc.buy(qty, price)
                net = c['net']
            else:
                c = Calc.sell(qty, price)
                net = c['net']

            self.db.run('''
                INSERT INTO transactions
                (trans_date,symbol,
                 company_name,trans_type,
                 quantity,price_per_share,
                 gross_amount,
                 broker_commission,sebon_fee,
                 dp_charge,
                 capital_market_fee,
                 total_charges,net_amount,
                 broker_name)
                VALUES(?,?,?,?,?,?,?,?,?,
                       ?,?,?,?,?)
            ''', (
                date, sym, comp, ttype,
                qty, price, c['gross'],
                c['broker'], c['sebon'],
                c['dp'], c.get('cm', 0),
                c['charges'], net, brok
            ))
            show_msg(
                'Saved!',
                f'{ttype}: {qty} x {sym}\n'
                f'@ Rs {price:,.2f}\n'
                f'Net: Rs {net:,.2f}')
            self._clear()
        except Exception as e:
            show_msg('Error', str(e))

    def _clear(self):
        self.f_date.text = (
            str(datetime.date.today()))
        for f in [self.f_sym, self.f_comp,
                  self.f_qty, self.f_price,
                  self.f_brok]:
            f.text = ''
        self.preview.text = 'Tap Calculate'


# ══════════════════════════════
# WATCHLIST SCREEN
# ══════════════════════════════
class WatchScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='watch', **kw)
        self.db = DB.get()
        self._built = False

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True
        self._update()

    def _build(self):
        root = BoxLayout(orientation='vertical')
        set_bg(root, BG)

        hdr = L('Watchlist', size=16,
                bold=True, color=PURPLE,
                height=46, halign='center')

        # Add form
        form_card = BoxLayout(
            orientation='vertical',
            padding=dp(10),
            spacing=dp(5),
            size_hint_y=None,
            height=dp(200))
        set_card_bg(form_card, CARD)

        form_card.add_widget(L(
            'Add to Watchlist',
            size=12, bold=True,
            color=CYAN, height=25))

        r1 = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(5))
        self.w_sym = I('Symbol', height=40)
        self.w_comp = I('Company', height=40)
        r1.add_widget(self.w_sym)
        r1.add_widget(self.w_comp)
        form_card.add_widget(r1)

        r2 = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(5))
        self.w_buy = I('Buy target Rs',
            input_filter='float', height=40)
        self.w_sell = I('Sell target Rs',
            input_filter='float', height=40)
        r2.add_widget(self.w_buy)
        r2.add_widget(self.w_sell)
        form_card.add_widget(r2)

        self.w_notes = I(
            'Notes (optional)', height=40)
        form_card.add_widget(self.w_notes)

        r3 = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(5))
        r3.add_widget(B(
            'Add', self._add_watch,
            bg=GREEN, height=40))
        r3.add_widget(B(
            'Clear', self._clear_form,
            bg=DIM, height=40))
        form_card.add_widget(r3)

        # Watchlist items
        sv = ScrollView(do_scroll_x=False)
        self.wbox = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(5),
            padding=dp(8))
        self.wbox.bind(
            minimum_height=
            self.wbox.setter('height'))
        sv.add_widget(self.wbox)

        nav = make_nav(self.manager, 'watch')

        root.add_widget(hdr)
        root.add_widget(form_card)
        root.add_widget(sv)
        root.add_widget(nav)
        self.add_widget(root)

    def _add_watch(self):
        try:
            sym = (self.w_sym.text
                   .upper().strip())
            comp = self.w_comp.text.strip()
            buy = float(
                self.w_buy.text or '0')
            sell = float(
                self.w_sell.text or '0')
            notes = self.w_notes.text.strip()

            if not sym:
                show_msg('Error',
                         'Symbol required!')
                return

            self.db.run('''
                INSERT OR REPLACE INTO
                watchlist(symbol, company,
                    target_buy, target_sell,
                    notes, added_date)
                VALUES(?,?,?,?,?,?)
            ''', (
                sym, comp, buy, sell, notes,
                str(datetime.date.today())
            ))
            show_msg(
                'Added!',
                f'{sym} added to watchlist')
            self._clear_form()
            self._update()
        except Exception as e:
            show_msg('Error', str(e))

    def _clear_form(self):
        for f in [self.w_sym, self.w_comp,
                  self.w_buy, self.w_sell,
                  self.w_notes]:
            f.text = ''

    def _remove(self, sym):
        self.db.run(
            'DELETE FROM watchlist'
            ' WHERE symbol=?', (sym,))
        self._update()

    def _update(self):
        self.wbox.clear_widgets()
        wls = self.db.all(
            'SELECT * FROM watchlist'
            ' ORDER BY symbol')

        if not wls:
            self.wbox.add_widget(L(
                '  No watchlist items.\n'
                '  Add stocks to watch.',
                size=12, color=DIM,
                height=60))
            return

        for w in wls:
            sym = w['symbol']
            pc = self.db.one(
                'SELECT * FROM prices'
                ' WHERE symbol=?', (sym,))
            cmp_ = pc['price'] if pc else 0

            buy = w['target_buy'] or 0
            sell = w['target_sell'] or 0

            # Determine status
            status = ''
            status_c = DIM
            if cmp_ and buy and cmp_ <= buy:
                status = 'BUY NOW!'
                status_c = GREEN
            elif cmp_ and sell and cmp_ >= sell:
                status = 'SELL NOW!'
                status_c = GREEN
            elif cmp_ and buy:
                diff = cmp_ - buy
                status = (
                    f'Rs {diff:+.2f} vs buy')
                status_c = (
                    ORANGE if diff > 0
                    else YELLOW)

            card = BoxLayout(
                orientation='vertical',
                padding=dp(10),
                spacing=dp(3),
                size_hint_y=None,
                height=dp(120))
            set_card_bg(card, CARD, 6)

            top = BoxLayout(
                size_hint_y=None,
                height=dp(25))
            top.add_widget(L(
                f"[b]{sym}[/b] "
                f"{w['company'][:20]}",
                size=12, markup=True,
                color=TEXT))
            rm_btn = Button(
                text='X',
                font_size=sp(11),
                background_normal='',
                background_color=RED,
                color=WHITE,
                size_hint_x=None,
                width=dp(30))
            rm_btn.bind(
                on_press=lambda x, s=sym:
                self._remove(s))
            top.add_widget(rm_btn)
            card.add_widget(top)

            info = L(
                f"CMP: Rs {cmp_:,.2f}"
                f"  Buy: Rs {buy:,.2f}"
                f"  Sell: Rs {sell:,.2f}",
                size=10, color=DIM, height=20)
            card.add_widget(info)

            if status:
                card.add_widget(L(
                    status, size=11,
                    color=status_c,
                    bold=True, height=22))

            if w['notes']:
                card.add_widget(L(
                    w['notes'], size=9,
                    color=DIM, height=18))

            self.wbox.add_widget(card)


# ══════════════════════════════
# MANUAL PRICE ENTRY SCREEN
# ══════════════════════════════
class ManualScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='manual', **kw)
        self.db = DB.get()
        self._built = False

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True
        self._update()

    def _build(self):
        root = BoxLayout(orientation='vertical')
        set_bg(root, BG)

        hdr = L('Manual Price Entry', size=15,
                bold=True, color=ORANGE,
                height=46, halign='center')

        # Info
        info = L(
            '  Enter prices manually for any stock\n'
            '  100% legal, no internet needed',
            size=10, color=CYAN, height=40)

        # Add manual price form
        form_card = BoxLayout(
            orientation='vertical',
            padding=dp(10),
            spacing=dp(5),
            size_hint_y=None,
            height=dp(180))
        set_card_bg(form_card, CARD)

        self.m_sym = I('Stock Symbol')
        form_card.add_widget(self.m_sym)

        self.m_price = I(
            'Current Price Rs',
            input_filter='float')
        form_card.add_widget(self.m_price)

        r1 = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(5))
        self.m_high = I(
            'Day High (opt)',
            input_filter='float', height=40)
        self.m_low = I(
            'Day Low (opt)',
            input_filter='float', height=40)
        r1.add_widget(self.m_high)
        r1.add_widget(self.m_low)
        form_card.add_widget(r1)

        form_card.add_widget(B(
            'Save Price', self._save,
            bg=GREEN, height=44))

        # Current manual prices
        sv = ScrollView(do_scroll_x=False)
        self.pbox = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(5),
            padding=dp(8))
        self.pbox.bind(
            minimum_height=
            self.pbox.setter('height'))
        sv.add_widget(self.pbox)

        nav = make_nav(self.manager, 'manual')

        root.add_widget(hdr)
        root.add_widget(info)
        root.add_widget(form_card)
        root.add_widget(sv)
        root.add_widget(nav)
        self.add_widget(root)

    def _save(self):
        try:
            sym = (self.m_sym.text
                   .upper().strip())
            price = float(
                self.m_price.text or '0')

            if not sym or price <= 0:
                show_msg('Error',
                         'Symbol & Price needed!')
                return

            try:
                high = float(
                    self.m_high.text or '0')
            except Exception:
                high = 0
            try:
                low = float(
                    self.m_low.text or '0')
            except Exception:
                low = 0

            # Get existing price for prev
            existing = self.db.one(
                'SELECT price FROM prices'
                ' WHERE symbol=?', (sym,))
            prev = (existing['price']
                    if existing else 0)

            data = {
                'price': price,
                'prev': prev,
                'high': high or price,
                'low': low or price,
                'vol': 0,
            }
            self.db.save_price(
                sym, data, 'Manual')

            show_msg(
                'Saved!',
                f'{sym} price: Rs {price:,.2f}')

            self.m_sym.text = ''
            self.m_price.text = ''
            self.m_high.text = ''
            self.m_low.text = ''
            self._update()
        except Exception as e:
            show_msg('Error', str(e))

    def _update(self):
        self.pbox.clear_widgets()
        prices = self.db.all(
            'SELECT * FROM prices'
            ' ORDER BY updated DESC LIMIT 30')

        if not prices:
            self.pbox.add_widget(L(
                '  No prices saved yet.',
                size=12, color=DIM,
                height=50))
            return

        self.pbox.add_widget(L(
            '  Recent Prices:',
            size=11, color=CYAN,
            bold=True, height=25))

        for p in prices:
            card = BoxLayout(
                orientation='horizontal',
                padding=dp(8),
                size_hint_y=None,
                height=dp(45))
            set_card_bg(card, CARD, 5)
            card.add_widget(L(
                f"[b]{p['symbol']}[/b]",
                size=11, markup=True,
                size_hint_x=0.25))
            card.add_widget(L(
                f"Rs {p['price']:,.2f}",
                size=11, color=BLUE,
                size_hint_x=0.3,
                halign='center'))
            src = (p['source']
                   if 'source' in p.keys()
                   and p['source']
                   else 'Unknown')
            card.add_widget(L(
                src, size=9,
                color=DIM,
                size_hint_x=0.25,
                halign='center'))
            try:
                dt = p['updated'][11:16]
            except Exception:
                dt = ''
            card.add_widget(L(
                dt, size=9,
                color=DIM,
                size_hint_x=0.2,
                halign='right'))
            self.pbox.add_widget(card)


# ══════════════════════════════
# INFO SCREEN
# ══════════════════════════════
class InfoScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='info', **kw)
        self._built = False

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True

    def _build(self):
        root = BoxLayout(orientation='vertical')
        set_bg(root, BG)

        hdr = L('About & Info', size=15,
                bold=True, color=BLUE,
                height=46, halign='center')

        sv = ScrollView(do_scroll_x=False)

        info_text = (
            "[b]NEPSE Portfolio Tracker v2.0[/b]\n\n"
            f"{'─'*32}\n\n"
            "[b]FEATURES:[/b]\n"
            "• Portfolio tracking with WACC\n"
            "• Manual price entry\n"
            "• Auto-fetch from 3rd parties\n"
            "• NEPSE Index tracking\n"
            "• Watchlist with alerts\n"
            "• All SEBON charges\n"
            "• CGT: 7.5% short / 10% long\n"
            "• Buy/Sell target prices\n\n"
            f"{'─'*32}\n\n"
            "[b][color=40D5E0]DATA SOURCES:[/color][/b]\n\n"
            "Third-party public sources only:\n"
            "• ShareSansar.com\n"
            "• NEPSE Alpha.com\n"
            "• MeroLagani.com\n\n"
            "[b]No direct NEPSE fetching[/b]\n\n"
            f"{'─'*32}\n\n"
            "[b][color=D29922]RATE LIMITING:[/color][/b]\n\n"
            "• 3 seconds between fetches\n"
            "• Auto-refresh: every 10 min\n"
            "• Manual: max 1 per minute\n"
            "• Only in market hours\n\n"
            f"{'─'*32}\n\n"
            "[b]CHARGES (SEBON):[/b]\n"
            "• Broker: 0.24%-0.40%\n"
            "• SEBON: 0.015%\n"
            "• DP: Rs 25\n"
            "• CM Fee: 0.2% (BUY only)\n"
            "• Min broker: Rs 10\n\n"
            "[b]CGT:[/b]\n"
            "• Held ≤ 365 days: 7.5%\n"
            "• Held > 365 days: 10%\n"
            "• Dividend TDS: 5%\n\n"
            "[b]MARKET HOURS:[/b]\n"
            "• Monday to Friday\n"
            "• 11:00 AM - 3:00 PM\n\n"
            f"{'─'*32}\n\n"
            "[b][color=D29922]DATA & PRIVACY:[/color][/b]\n\n"
            "• All data stored on YOUR device\n"
            "• No accounts required\n"
            "• No data sent anywhere\n"
            "• 100% offline capable\n"
            "• (with manual entry)\n\n"
            f"{'─'*32}\n\n"
            "[b][color=D29922]DISCLAIMER:[/color][/b]\n\n"
            "For personal use only.\n"
            "Price data from public sources.\n"
            "Not affiliated with NEPSE, SEBON,\n"
            "or any broker.\n\n"
            "[b]Verify prices from official\n"
            "sources before investing.[/b]\n\n"
            "All calculations are estimates.\n"
            "Consult your broker for actual\n"
            "transaction charges.\n\n"
            f"{'─'*32}\n\n"
            "Made with care for the\n"
            "Nepal investor community 🇳🇵\n\n"
        )

        info_lbl = Label(
            text=info_text,
            font_size=sp(12),
            color=TEXT,
            markup=True,
            halign='left',
            size_hint_y=None,
            padding=(dp(15), dp(10)))
        info_lbl.bind(
            size=lambda i, v:
            setattr(i, 'text_size',
                    (v[0]-dp(20), None)),
            texture_size=lambda i, v:
            setattr(i, 'height',
                    v[1] + dp(20)))

        sv.add_widget(info_lbl)

        nav = make_nav(self.manager, 'info')
        root.add_widget(hdr)
        root.add_widget(sv)
        root.add_widget(nav)
        self.add_widget(root)


# ══════════════════════════════
# MAIN APP
# ══════════════════════════════
class NEPSEApp(App):
    def build(self):
        self.title = 'NEPSE Tracker'
        DB.get()

        sm = ScreenManager(
            transition=SlideTransition())
        sm.add_widget(DashScreen())
        sm.add_widget(PortScreen())
        sm.add_widget(AddScreen())
        sm.add_widget(WatchScreen())
        sm.add_widget(ManualScreen())
        sm.add_widget(InfoScreen())

        Clock.schedule_interval(
            self._auto_refresh,
            AUTO_REFRESH_MINUTES * 60)

        return sm

    def _auto_refresh(self, dt):
        """Ethical auto-refresh"""
        if MARKET_ONLY_AUTO:
            if not Calc.is_open():
                return

        db = DB.get()
        syms = db.all(
            'SELECT DISTINCT symbol'
            ' FROM transactions'
            ' WHERE trans_type="BUY"')

        if not syms:
            return

        def fetch():
            # NEPSE Index
            idx = Fetcher.fetch_nepse_index()
            if idx:
                db.save_index(idx)

            # Portfolio prices
            for s in syms:
                d = Fetcher.fetch_price(
                    s['symbol'])
                if d:
                    db.save_price(
                        s['symbol'], d,
                        d.get('source',''))

        threading.Thread(
            target=fetch,
            daemon=True).start()

    def on_stop(self):
        db = DB.get()
        if db.conn:
            db.conn.close()


if __name__ == '__main__':
    NEPSEApp().run()
