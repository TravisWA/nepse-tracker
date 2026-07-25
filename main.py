"""
NEPSE Portfolio Tracker - Android App
Complete stock portfolio management for Nepal
"""

import os
import sys
import sqlite3
import datetime
import threading

# ── Kivy Setup ───────────────────────────────────
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

# ════════════════════════════════════════════════
# COLORS
# ════════════════════════════════════════════════
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

def hex_to_rgb(h):
    h = h.lstrip('#')
    r,g,b = (int(h[i:i+2],16)/255
              for i in (0,2,4))
    return [r,g,b,1]


# ════════════════════════════════════════════════
# NEPAL CHARGE CALCULATOR
# All charges per SEBON regulations
# CGT: 7.5% short term, 10% long term
# Market: Monday-Friday 11AM-3PM
# ════════════════════════════════════════════════
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
            return f'🟢 OPEN {rem}min'
        days = ['Mon','Tue','Wed',
                'Thu','Fri','Sat','Sun']
        return f'🔴 {days[now.weekday()]}'


# ════════════════════════════════════════════════
# DATABASE
# ════════════════════════════════════════════════
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
                updated TEXT
            );

            CREATE TABLE IF NOT EXISTS
            dividends (
                id INTEGER PRIMARY KEY
                   AUTOINCREMENT,
                record_date TEXT,
                symbol TEXT,
                div_type TEXT,
                rate REAL DEFAULT 0,
                gross REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                net REAL DEFAULT 0,
                notes TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS
            corp_actions (
                id INTEGER PRIMARY KEY
                   AUTOINCREMENT,
                action_date TEXT,
                symbol TEXT,
                action_type TEXT,
                details TEXT DEFAULT '',
                new_shares INTEGER DEFAULT 0,
                cost_added REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS
            watchlist (
                symbol TEXT PRIMARY KEY,
                company TEXT DEFAULT '',
                target_price REAL DEFAULT 0,
                notes TEXT DEFAULT '',
                added_date TEXT
            );

            CREATE TABLE IF NOT EXISTS
            app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        ''')
        # Default settings
        defaults = [
            ('target1', '10'),
            ('target2', '20'),
            ('target3', '30'),
            ('app_version', '1.0'),
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

    def save_price(self, sym, data):
        self.run('''
            INSERT OR REPLACE INTO prices
            (symbol,price,prev_close,
             day_high,day_low,volume,updated)
            VALUES(?,?,?,?,?,?,?)
        ''', (
            sym,
            data.get('price', 0),
            data.get('prev', 0),
            data.get('high', 0),
            data.get('low', 0),
            data.get('vol', 0),
            str(datetime.datetime.now())
        ))

    def setting(self, key, default=''):
        r = self.one(
            'SELECT value FROM app_settings'
            ' WHERE key=?', (key,))
        return r['value'] if r else default

    def set_setting(self, key, value):
        self.run(
            '''INSERT OR REPLACE INTO
               app_settings(key,value)
               VALUES(?,?)''',
            (key, str(value)))


# ════════════════════════════════════════════════
# DATA FETCHER
# Legal - Public NEPSE Sources
# ════════════════════════════════════════════════
class Fetcher:
    UA = {
        'User-Agent': (
            'Mozilla/5.0 (Linux; Android 10)'
            ' AppleWebKit/537.36'
        )
    }

    @classmethod
    def fetch(cls, symbol):
        import time
        time.sleep(1.2)

        # Source 1: NEPSE Official API
        try:
            import requests
            r = requests.get(
                'https://nepalstock.com.np'
                '/api/nots/nepse-data'
                '/today-price',
                headers=cls.UA,
                timeout=10,
                verify=True
            )
            if r.status_code == 200:
                for item in r.json().get(
                        'content', []):
                    if (item.get('symbol', '')
                            .upper() ==
                            symbol.upper()):
                        return {
                            'price': float(
                                item.get(
                                'lastTradedPrice',
                                0)),
                            'prev': float(
                                item.get(
                                'previousClose',
                                0)),
                            'high': float(
                                item.get(
                                'highPrice',0)),
                            'low': float(
                                item.get(
                                'lowPrice',0)),
                            'vol': int(item.get(
                                'totalTrade'
                                'Quantity',0)),
                        }
        except Exception:
            pass

        # Source 2: MeroLagani
        try:
            import requests
            from bs4 import BeautifulSoup
            time.sleep(1.0)
            url = (
                'https://merolagani.com'
                '/CompanyDetail.aspx'
                f'?symbol={symbol.upper()}'
            )
            r = requests.get(
                url, headers=cls.UA,
                timeout=10, verify=True)
            if r.status_code == 200:
                soup = BeautifulSoup(
                    r.text, 'html.parser')
                pre = (
                    'ctl00_ContentPlaceHolder1_'
                    'CompanyDetail1_lbl'
                )
                def gv(f):
                    el = soup.find(
                        'span', {'id': pre+f})
                    if el:
                        try:
                            return float(
                                el.text.strip()
                                .replace(',',''))
                        except Exception:
                            return 0
                    return 0
                p = gv('MarketPrice')
                if p > 0:
                    return {
                        'price': p,
                        'prev': gv(
                            'PreviousClose'),
                        'high': gv('High'),
                        'low': gv('Low'),
                        'vol': 0,
                    }
        except Exception:
            pass

        return None


# ════════════════════════════════════════════════
# PORTFOLIO ENGINE
# ════════════════════════════════════════════════
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
        cmp  = pc['price'] if pc else 0
        prev = pc['prev_close'] if pc else 0
        high = pc['day_high'] if pc else 0
        low  = pc['day_low'] if pc else 0
        vol  = pc['volume'] if pc else 0

        cv   = cq * cmp if cmp else 0
        upl  = cv - tc if cmp else 0
        plp  = (upl / tc * 100
                if tc and cmp else 0)
        dchg = (cmp - prev
                if cmp and prev else 0)
        dpct = (dchg / prev * 100
                if prev and cmp else 0)

        sc   = (Calc.sell(cq, cmp)
                if cmp else {})
        ca, cl = (
            Calc.cgt(upl, first)
            if upl > 0
            else (0, 'No Tax')
        )
        netp = (upl
                - sc.get('charges', 0)
                - ca
                if cmp else 0)
        npct = (netp / tc * 100
                if tc and cmp else 0)

        be  = Calc.breakeven(wacc, cq)
        t1  = float(
            self.db.setting('target1','10'))
        t2  = float(
            self.db.setting('target2','20'))
        t3  = float(
            self.db.setting('target3','30'))
        tp1 = Calc.target(wacc,cq,first,t1)
        tp2 = Calc.target(wacc,cq,first,t2)
        tp3 = Calc.target(wacc,cq,first,t3)

        sig, scol = self._signal(
            cmp, wacc, be, tp1)

        dr = self.db.one(
            'SELECT SUM(net) as tot'
            ' FROM dividends'
            ' WHERE symbol=?', (symbol,))
        divs = (dr['tot'] or 0) if dr else 0

        return {
            'symbol':   symbol,
            'company':  (txns[0]['company_name']
                         or symbol),
            'sector':   txns[0]['sector'] or '',
            'first':    first,
            'hold':     hold,
            'bq': bq, 'sq': sq, 'cq': cq,
            'wacc': round(wacc, 2),
            'tc':   round(tc, 2),
            'cmp':  cmp,
            'prev': prev,
            'high': high,
            'low':  low,
            'vol':  vol,
            'dchg': round(dchg, 2),
            'dpct': round(dpct, 2),
            'cv':   round(cv, 2),
            'upl':  round(upl, 2),
            'plp':  round(plp, 2),
            'sell_broker': round(
                sc.get('broker', 0), 2),
            'sell_sebon':  round(
                sc.get('sebon', 0), 2),
            'sell_dp':     sc.get('dp', 0),
            'sell_ch':     round(
                sc.get('charges', 0), 2),
            'cgt':  round(ca, 2),
            'cgtl': cl,
            'netp': round(netp, 2),
            'npct': round(npct, 2),
            'be':   be,
            'tp1':  tp1,
            'tp2':  tp2,
            'tp3':  tp3,
            't1':   t1, 't2': t2, 't3': t3,
            'sig':  sig,
            'scol': scol,
            'divs': round(divs, 2),
        }

    def _signal(self, cmp, wacc, be, tp1):
        if not cmp or cmp == 0:
            return '⚪ No Price', DIM
        if cmp >= tp1 * 1.15:
            return '🚀 Strong Sell!', GREEN
        if cmp >= tp1 * 1.05:
            return '🟢 Great Sell', GREEN
        if cmp >= tp1:
            return '✅ Target Hit!', GREEN
        if cmp >= be:
            return '🟡 Hold (Profit)', YELLOW
        if cmp >= wacc * 0.95:
            return '🟠 Near Cost', ORANGE
        if cmp >= wacc * 0.85:
            return '🔴 Loss - Hold', RED
        return '🆘 Big Loss!', RED

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
                'n': 0, 'prof': 0,
                'loss': 0, 'divs': 0,
            }
        inv  = sum(h['tc']      for h in hs)
        val  = sum(h['cv']      for h in hs)
        pl   = val - inv
        cgt  = sum(h['cgt']     for h in hs)
        sc   = sum(h['sell_ch'] for h in hs)
        divs = sum(h['divs']    for h in hs)
        return {
            'inv':  round(inv, 2),
            'val':  round(val, 2),
            'pl':   round(pl, 2),
            'plp':  round(
                pl/inv*100 if inv else 0, 2),
            'cgt':  round(cgt, 2),
            'net':  round(val-cgt-sc, 2),
            'n':    len(hs),
            'prof': sum(1 for h in hs
                        if h['upl'] > 0),
            'loss': sum(1 for h in hs
                        if h['upl'] < 0),
            'divs': round(divs, 2),
        }


# ════════════════════════════════════════════════
# UI HELPERS
# ════════════════════════════════════════════════
def set_bg(widget, color):
    with widget.canvas.before:
        Color(*color)
        Rectangle(
            pos=widget.pos,
            size=widget.size)
    widget.bind(
        pos=lambda i, v:
        _redraw_bg(i, color),
        size=lambda i, v:
        _redraw_bg(i, color))


def _redraw_bg(widget, color):
    widget.canvas.before.clear()
    with widget.canvas.before:
        Color(*color)
        Rectangle(
            pos=widget.pos,
            size=widget.size)


def set_card_bg(widget, color=None,
                radius=8):
    c = color or CARD
    with widget.canvas.before:
        Color(*c)
        RoundedRectangle(
            pos=widget.pos,
            size=widget.size,
            radius=[dp(radius)])
    widget.bind(
        pos=lambda i, v:
        _redraw_card(i, c, radius),
        size=lambda i, v:
        _redraw_card(i, c, radius))


def _redraw_card(widget, color, radius):
    widget.canvas.before.clear()
    with widget.canvas.before:
        Color(*color)
        RoundedRectangle(
            pos=widget.pos,
            size=widget.size,
            radius=[dp(radius)])


def make_label(text, size=13,
               color=None, bold=False,
               halign='left',
               height=None, **kw):
    lbl = Label(
        text=text,
        font_size=sp(size),
        color=color or TEXT,
        bold=bold,
        halign=halign,
        **kw
    )
    lbl.bind(size=lambda i, v:
             setattr(i, 'text_size',
                     (v[0], None)))
    if height:
        lbl.size_hint_y = None
        lbl.height = dp(height)
    return lbl


def make_button(text, callback,
                bg=None, height=48,
                font_size=13, **kw):
    btn = Button(
        text=text,
        font_size=sp(font_size),
        background_normal='',
        background_color=bg or BLUE,
        color=WHITE,
        size_hint_y=None,
        height=dp(height),
        **kw
    )
    btn.bind(on_press=lambda x: callback())
    return btn


def make_input(hint='', text='',
               height=46,
               input_filter=None,
               multiline=False,
               **kw):
    ti = TextInput(
        hint_text=hint,
        text=str(text),
        multiline=multiline,
        font_size=sp(13),
        background_color=CARD2,
        foreground_color=TEXT,
        hint_text_color=DIM,
        cursor_color=BLUE,
        size_hint_y=None,
        height=dp(height),
        padding=[dp(12), dp(10)],
        **kw
    )
    if input_filter:
        ti.input_filter = input_filter
    return ti


def make_spinner(values, current=None,
                 height=46, **kw):
    sp_ = Spinner(
        text=current or values[0],
        values=values,
        font_size=sp(12),
        background_normal='',
        background_color=CARD2,
        color=TEXT,
        size_hint_y=None,
        height=dp(height),
        **kw
    )
    return sp_


def show_msg(title, msg):
    content = BoxLayout(
        orientation='vertical',
        padding=dp(15),
        spacing=dp(10)
    )
    set_bg(content, CARD)

    lbl = Label(
        text=msg,
        font_size=sp(12),
        color=TEXT,
        halign='left',
        size_hint_y=None,
    )
    lbl.bind(
        size=lambda i, v:
        setattr(i, 'text_size',
                (v[0], None)),
        texture_size=lambda i, v:
        setattr(i, 'height', v[1]+dp(10))
    )

    ok = make_button('OK ✓', lambda: None,
                     bg=BLUE, height=44)

    popup = Popup(
        title=title,
        title_color=BLUE,
        title_size=sp(14),
        content=content,
        size_hint=(0.88, None),
        height=dp(220),
        background='',
        background_color=CARD,
        separator_color=CARD2,
    )
    ok.bind(on_press=popup.dismiss)
    content.add_widget(lbl)
    content.add_widget(ok)
    popup.open()


def make_nav(sm, current_name):
    """Bottom navigation bar"""
    items = [
        ('📊', 'dash',    'Home'),
        ('📈', 'port',    'Portfolio'),
        ('➕', 'add',     'Add'),
        ('💰', 'calc',    'Calc'),
        ('🎁', 'bonus',   'Bonus'),
        ('📋', 'history', 'History'),
    ]
    nav = BoxLayout(
        orientation='horizontal',
        size_hint_y=None,
        height=dp(58),
        spacing=dp(1),
    )
    set_bg(nav, BLACK)

    for icon, name, label in items:
        is_cur = (name == current_name)
        bg = BLUE if is_cur else CARD2
        btn = Button(
            text=f'{icon}\n{label}',
            font_size=sp(9),
            background_normal='',
            background_color=bg,
            color=WHITE,
            halign='center',
        )
        def _go(inst, n=name):
            sm.transition = SlideTransition(
                direction='left')
            sm.current = n
        btn.bind(on_press=_go)
        nav.add_widget(btn)

    return nav


# ════════════════════════════════════════════════
# SCREEN: DASHBOARD (HOME)
# ════════════════════════════════════════════════
class DashScreen(Screen):
    def __init__(self, **kw):
        super().__init__(
            name='dash', **kw)
        self.port = Portfolio()
        self._built = False

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True
        self._update()

    def _build(self):
        root = BoxLayout(
            orientation='vertical',
            spacing=0)
        set_bg(root, BG)

        # Header
        hdr = BoxLayout(
            size_hint_y=None,
            height=dp(52),
            padding=[dp(12), dp(8)],
            spacing=dp(8))
        set_bg(hdr, CARD)

        self.title_lbl = make_label(
            '🇳🇵 NEPSE Tracker',
            size=16, bold=True,
            color=BLUE, height=36)
        self.mkt_lbl = make_label(
            Calc.market_status(),
            size=10, color=GREEN,
            height=36, halign='right')
        hdr.add_widget(self.title_lbl)
        hdr.add_widget(self.mkt_lbl)

        # Refresh row
        ref_row = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            padding=[dp(8), dp(4)],
            spacing=dp(8))
        set_bg(ref_row, BG)

        ref_btn = make_button(
            '🔄 Refresh Prices',
            self._refresh,
            bg=GREEN, height=42)
        self.upd_lbl = make_label(
            'Tap Refresh',
            size=9, color=DIM,
            height=42,
            halign='right')
        ref_row.add_widget(ref_btn)
        ref_row.add_widget(self.upd_lbl)

        # Summary cards
        cards_grid = GridLayout(
            cols=2,
            size_hint_y=None,
            height=dp(210),
            spacing=dp(5),
            padding=[dp(8), dp(4)])
        set_bg(cards_grid, BG)

        self.card_lbl = {}
        card_cfg = [
            ('inv',  '💼 Invested', BLUE),
            ('val',  '📈 Value',    PURPLE),
            ('pl',   '💰 P/L',      GREEN),
            ('cgt',  '🏛️ CGT',       RED),
            ('net',  '🤑 Net',      GREEN),
            ('divs', '🎁 Dividends',YELLOW),
        ]
        for key, title, col in card_cfg:
            card = BoxLayout(
                orientation='vertical',
                padding=dp(8),
                size_hint_y=None,
                height=dp(95))
            set_card_bg(card, CARD)

            tl = make_label(
                title, size=9,
                color=DIM, height=20)
            vl = make_label(
                'Rs 0', size=14,
                bold=True, color=col,
                height=30)
            card.add_widget(tl)
            card.add_widget(vl)
            self.card_lbl[key] = vl
            cards_grid.add_widget(card)

        # Stats
        self.stats_lbl = make_label(
            '  Loading...',
            size=10, color=DIM,
            height=24)

        # Table header
        th = BoxLayout(
            size_hint_y=None,
            height=dp(28),
            padding=[dp(5), 0])
        set_bg(th, CARD2)
        for txt, sx in [
            ('Symbol', 0.22),
            ('CMP',    0.22),
            ('P/L%',   0.18),
            ('Signal', 0.38)
        ]:
            th.add_widget(make_label(
                txt, size=9, bold=True,
                color=BLUE,
                height=28,
                halign='center',
                size_hint_x=sx))

        # Holdings list
        sv = ScrollView(
            do_scroll_x=False)
        self.holdings_box = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(4),
            padding=[dp(6), dp(4)])
        self.holdings_box.bind(
            minimum_height=
            self.holdings_box.setter(
                'height'))
        sv.add_widget(self.holdings_box)

        # Nav
        nav = make_nav(self.manager, 'dash')

        root.add_widget(hdr)
        root.add_widget(ref_row)
        root.add_widget(cards_grid)
        root.add_widget(self.stats_lbl)
        root.add_widget(th)
        root.add_widget(sv)
        root.add_widget(nav)
        self.add_widget(root)

    def _update(self):
        t  = self.port.totals()
        hs = self.port.all_holdings()
        self.mkt_lbl.text = (
            Calc.market_status())

        # Cards
        self.card_lbl['inv'].text = (
            f"Rs {t['inv']:,.0f}")
        self.card_lbl['val'].text = (
            f"Rs {t['val']:,.0f}")
        pl  = t['pl']
        arr = '▲' if pl >= 0 else '▼'
        col = GREEN if pl >= 0 else RED
        self.card_lbl['pl'].text = (
            f"{arr} {abs(t['plp']):.1f}%"
            f"\nRs {abs(pl):,.0f}")
        self.card_lbl['pl'].color = col
        self.card_lbl['cgt'].text = (
            f"Rs {t['cgt']:,.0f}")
        self.card_lbl['net'].text = (
            f"Rs {t['net']:,.0f}")
        self.card_lbl['divs'].text = (
            f"Rs {t['divs']:,.0f}")

        self.stats_lbl.text = (
            f"  📦{t['n']} stocks  "
            f"🟢{t['prof']}  🔴{t['loss']}"
        )

        # Holdings rows
        self.holdings_box.clear_widgets()
        for h in hs:
            row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(58),
                padding=dp(6),
                spacing=dp(4))
            set_card_bg(row, CARD, 6)

            pl_c = (GREEN if h['plp'] >= 0
                    else RED)
            cmp_s = (f"Rs {h['cmp']:,.0f}"
                     if h['cmp'] else 'N/A')

            row.add_widget(make_label(
                f"[b]{h['symbol']}[/b]\n"
                f"{h['cq']}shr",
                size=11, markup=True,
                size_hint_x=0.22))
            row.add_widget(make_label(
                cmp_s, size=11,
                color=BLUE,
                size_hint_x=0.22,
                halign='center'))
            row.add_widget(make_label(
                (f"{h['plp']:.1f}%"
                 if h['cmp'] else 'N/A'),
                size=11, color=pl_c,
                size_hint_x=0.18,
                halign='center'))
            row.add_widget(make_label(
                h['sig'], size=9,
                color=h['scol'],
                size_hint_x=0.38,
                halign='center'))

            self.holdings_box.add_widget(
                row)

    def _refresh(self):
        self.upd_lbl.text = '⏳ Fetching...'
        db = DB.get()

        def fetch():
            syms = db.all(
                'SELECT DISTINCT symbol'
                ' FROM transactions'
                ' WHERE trans_type="BUY"')
            for s in syms:
                d = Fetcher.fetch(
                    s['symbol'])
                if d:
                    db.save_price(
                        s['symbol'], d)
            Clock.schedule_once(
                lambda dt:
                self._done_refresh(), 0)

        threading.Thread(
            target=fetch,
            daemon=True).start()

    @mainthread
    def _done_refresh(self):
        now = datetime.datetime.now()
        self.upd_lbl.text = (
            f"✅ "
            f"{now.strftime('%H:%M:%S')}")
        self._update()


# ════════════════════════════════════════════════
# SCREEN: PORTFOLIO DETAIL
# ════════════════════════════════════════════════
class PortScreen(Screen):
    def __init__(self, **kw):
        super().__init__(
            name='port', **kw)
        self.port = Portfolio()
        self._built = False

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True
        self._update()

    def _build(self):
        root = BoxLayout(
            orientation='vertical')
        set_bg(root, BG)

        hdr = make_label(
            '📈 Portfolio',
            size=16, bold=True,
            color=BLUE, height=48,
            halign='center')

        sv = ScrollView(
            do_scroll_x=False)
        self.detail_box = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(8),
            padding=dp(8))
        self.detail_box.bind(
            minimum_height=
            self.detail_box.setter(
                'height'))
        sv.add_widget(self.detail_box)

        nav = make_nav(
            self.manager, 'port')

        root.add_widget(hdr)
        root.add_widget(sv)
        root.add_widget(nav)
        self.add_widget(root)

    def _update(self):
        self.detail_box.clear_widgets()
        hs = self.port.all_holdings()

        if not hs:
            self.detail_box.add_widget(
                make_label(
                    '  No stocks yet.\n'
                    '  Go to ➕ Add tab\n'
                    '  to add your stocks.',
                    size=13, color=DIM,
                    height=100))
            return

        for h in hs:
            pl_c = (GREEN
                    if h['upl'] >= 0
                    else RED)
            cmp_s = (f"Rs {h['cmp']:,.2f}"
                     if h['cmp']
                     else 'Price N/A')

            card = BoxLayout(
                orientation='vertical',
                padding=dp(12),
                spacing=dp(2),
                size_hint_y=None)
            set_card_bg(card, CARD)

            txt = (
                f"[b][size={sp(15):.0f}]"
                f"{h['symbol']}[/size][/b]"
                f"  {h['company']}\n"
                f"{'─'*34}\n"
                f"Qty: [b]{h['cq']:,}[/b]"
                f"  WACC:"
                f" Rs {h['wacc']:,.2f}"
                f"  CMP: {cmp_s}\n"
                f"Cost: Rs {h['tc']:,.2f}"
                f"  Value:"
                f" Rs {h['cv']:,.2f}\n\n"
                f"P/L:"
                f" Rs {h['upl']:,.2f}"
                f" ({h['plp']:.2f}%)\n"
                f"Day:"
                f" Rs {h['dchg']:,.2f}"
                f" ({h['dpct']:.2f}%)\n\n"
                f"[b]── Sell Today ──[/b]\n"
                f"Broker: Rs {h['sell_broker']:,.2f}"
                f"  SEBON:"
                f" Rs {h['sell_sebon']:,.2f}"
                f"  DP: Rs {h['sell_dp']:.0f}\n"
                f"CGT ({h['cgtl']}):"
                f" Rs {h['cgt']:,.2f}\n"
                f"[b]Net Profit:"
                f" Rs {h['netp']:,.2f}"
                f" ({h['npct']:.1f}%)[/b]\n\n"
                f"[b]── Targets ──[/b]\n"
                f"Breakeven:"
                f" Rs {h['be']:,.2f}\n"
                f"Target {h['t1']:.0f}%:"
                f" Rs {h['tp1']:,.2f}\n"
                f"Target {h['t2']:.0f}%:"
                f" Rs {h['tp2']:,.2f}\n"
                f"Target {h['t3']:.0f}%:"
                f" Rs {h['tp3']:,.2f}\n\n"
                f"Held: {h['hold']} days"
                f"  Dividends:"
                f" Rs {h['divs']:,.2f}\n"
                f"[b]{h['sig']}[/b]"
            )

            lbl = Label(
                text=txt,
                font_size=sp(11),
                markup=True,
                halign='left',
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
            self.detail_box.add_widget(card)


# ════════════════════════════════════════════════
# SCREEN: ADD TRANSACTION
# ════════════════════════════════════════════════
class AddScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='add', **kw)
        self.db   = DB.get()
        self.port = Portfolio()
        self._built = False

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True
        self.f_date.text = (
            str(datetime.date.today()))

    def _build(self):
        root = BoxLayout(
            orientation='vertical')
        set_bg(root, BG)

        hdr = make_label(
            '➕ Add Transaction',
            size=15, bold=True,
            color=BLUE, height=46,
            halign='center')

        sv = ScrollView(
            do_scroll_x=False)
        form = GridLayout(
            cols=1, spacing=dp(6),
            padding=dp(10),
            size_hint_y=None)
        form.bind(
            minimum_height=
            form.setter('height'))

        def field(lbl, widget):
            b = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=dp(78),
                spacing=dp(2))
            b.add_widget(make_label(
                lbl, size=11,
                color=DIM, height=22))
            b.add_widget(widget)
            return b

        self.f_date = make_input(
            'Date YYYY-MM-DD',
            str(datetime.date.today()))
        self.f_sym  = make_input(
            'Symbol e.g. NABIL')
        self.f_comp = make_input(
            'Company Name')
        self.f_qty  = make_input(
            'Quantity',
            input_filter='int')
        self.f_price= make_input(
            'Price per Share Rs',
            input_filter='float')
        self.f_brok = make_input(
            'Broker Name')
        self.f_type = make_spinner(
            ['BUY','SELL'])
        self.f_sect = make_spinner([
            'Banking','Finance',
            'Insurance','Hydropower',
            'Manufacturing','Trading',
            'Hotel','Microfinance','Others'])

        form.add_widget(field(
            '📅 Date', self.f_date))
        form.add_widget(field(
            '🏷️ Symbol', self.f_sym))
        form.add_widget(field(
            '🏢 Company', self.f_comp))
        form.add_widget(field(
            '📊 Type', self.f_type))
        form.add_widget(field(
            '🏭 Sector', self.f_sect))
        form.add_widget(field(
            '🔢 Quantity', self.f_qty))
        form.add_widget(field(
            '💵 Price/Share Rs',
            self.f_price))
        form.add_widget(field(
            '🏦 Broker', self.f_brok))

        # Charge preview
        self.preview = Label(
            text='Tap Calculate to see charges',
            font_size=sp(11),
            color=GREEN,
            markup=True,
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

        # Buttons
        btn_row = BoxLayout(
            size_hint_y=None,
            height=dp(52),
            spacing=dp(8),
            padding=[0, dp(4)])
        btn_row.add_widget(make_button(
            '🔢 Calc', self._calc,
            bg=YELLOW, height=44))
        btn_row.add_widget(make_button(
            '✅ Save', self._save,
            bg=GREEN, height=44))
        btn_row.add_widget(make_button(
            '🗑️ Clear', self._clear,
            bg=DIM, height=44))

        form.add_widget(btn_row)
        sv.add_widget(form)

        nav = make_nav(
            self.manager, 'add')

        root.add_widget(hdr)
        root.add_widget(sv)
        root.add_widget(nav)
        self.add_widget(root)

    def _calc(self):
        try:
            qty   = int(
                self.f_qty.text or '0')
            price = float(
                self.f_price.text or '0')
            ttype = self.f_type.text
            sym   = self.f_sym.text.upper()

            if qty <= 0 or price <= 0:
                self.preview.text = (
                    '⚠️ Enter Qty and Price!')
                return

            if ttype == 'BUY':
                c = Calc.buy(qty, price)
                h = self.port.holding(sym)
                wacc_info = ''
                if h and sym:
                    nq = h['bq'] + qty
                    nc = h['tc'] + c['net']
                    nw = nc / nq
                    wacc_info = (
                        f"\n📊 New WACC:"
                        f" Rs {nw:,.2f}"
                        f"  (was Rs {h['wacc']:,.2f})")
                else:
                    wacc_info = (
                        f"\n📊 WACC:"
                        f" Rs {c['wacc']:,.2f}")

                self.preview.text = (
                    f"[b]── BUY CHARGES ──[/b]\n"
                    f"Gross :"
                    f" Rs {c['gross']:>10,.2f}\n"
                    f"Broker:"
                    f" Rs {c['broker']:>10,.2f}\n"
                    f"SEBON :"
                    f" Rs {c['sebon']:>10,.2f}\n"
                    f"DP    :"
                    f" Rs {c['dp']:>10.2f}\n"
                    f"CM Fee:"
                    f" Rs {c['cm']:>10,.2f}\n"
                    f"──────────────────────\n"
                    f"Charges:"
                    f" Rs {c['charges']:>9,.2f}\n"
                    f"[b]NET COST:"
                    f" Rs {c['net']:,.2f}[/b]"
                    f"{wacc_info}"
                )
            else:
                c   = Calc.sell(qty, price)
                h   = self.port.holding(sym)
                tax_info = ''
                if h and sym:
                    profit = (c['net']
                              - h['wacc']*qty)
                    ca, cl = Calc.cgt(
                        profit, h['first'])
                    tax_info = (
                        f"\n📊 WACC:"
                        f" Rs {h['wacc']:,.2f}"
                        f"\nGross P/L:"
                        f" Rs {profit:,.2f}"
                        f"\nCGT ({cl}):"
                        f" Rs {ca:,.2f}"
                        f"\nNet:"
                        f" Rs {profit-ca:,.2f}")

                self.preview.text = (
                    f"[b]── SELL CHARGES ──[/b]\n"
                    f"Gross :"
                    f" Rs {c['gross']:>10,.2f}\n"
                    f"Broker:"
                    f" Rs {c['broker']:>10,.2f}\n"
                    f"SEBON :"
                    f" Rs {c['sebon']:>10,.2f}\n"
                    f"DP    :"
                    f" Rs {c['dp']:>10.2f}\n"
                    f"──────────────────────\n"
                    f"Charges:"
                    f" Rs {c['charges']:>9,.2f}\n"
                    f"[b]NET PROCEEDS:"
                    f" Rs {c['net']:,.2f}[/b]"
                    f"{tax_info}"
                )

        except (ValueError, TypeError):
            self.preview.text = (
                '⚠️ Check Quantity & Price!')

    def _save(self):
        try:
            date  = self.f_date.text.strip()
            sym   = (self.f_sym.text
                     .upper().strip())
            comp  = self.f_comp.text.strip()
            sect  = self.f_sect.text
            ttype = self.f_type.text
            qty   = int(
                self.f_qty.text or '0')
            price = float(
                self.f_price.text or '0')
            brok  = self.f_brok.text.strip()

            if not sym:
                show_msg('⚠️ Error',
                         'Symbol is required!')
                return
            if qty <= 0 or price <= 0:
                show_msg('⚠️ Error',
                         'Enter valid Qty'
                         ' and Price!')
                return

            if ttype == 'BUY':
                c   = Calc.buy(qty, price)
                net = c['net']
            else:
                c   = Calc.sell(qty, price)
                net = c['net']

            self.db.run('''
                INSERT INTO transactions
                (trans_date, symbol,
                 company_name, sector,
                 trans_type, quantity,
                 price_per_share,
                 gross_amount,
                 broker_commission,
                 sebon_fee, dp_charge,
                 capital_market_fee,
                 total_charges, net_amount,
                 broker_name)
                VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                date, sym, comp, sect,
                ttype, qty, price,
                c['gross'], c['broker'],
                c['sebon'], c['dp'],
                c.get('cm', 0),
                c['charges'], net, brok,
            ))

            show_msg(
                '✅ Saved!',
                f"{ttype}: {qty:,} × {sym}\n"
                f"@ Rs {price:,.2f}/share\n"
                f"Charges:"
                f" Rs {c['charges']:,.2f}\n"
                f"Net: Rs {net:,.2f}"
            )
            self._clear()

        except ValueError:
            show_msg('⚠️ Error',
                     'Invalid numbers!')
        except Exception as e:
            show_msg('❌ Error', str(e))

    def _clear(self):
        self.f_date.text = (
            str(datetime.date.today()))
        for f in [self.f_sym, self.f_comp,
                  self.f_qty, self.f_price,
                  self.f_brok]:
            f.text = ''
        self.preview.text = (
            'Tap Calculate to see charges')


# ════════════════════════════════════════════════
# SCREEN: CHARGE CALCULATOR
# ════════════════════════════════════════════════
class CalcScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='calc', **kw)
        self._built = False

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True

    def _build(self):
        root = BoxLayout(
            orientation='vertical')
        set_bg(root, BG)

        hdr = make_label(
            '💰 Charge Calculator',
            size=15, bold=True,
            color=BLUE, height=46,
            halign='center')

        sv = ScrollView(
            do_scroll_x=False)
        form = GridLayout(
            cols=1, spacing=dp(5),
            padding=dp(10),
            size_hint_y=None)
        form.bind(
            minimum_height=
            form.setter('height'))

        def field(lbl, widget):
            b = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=dp(75),
                spacing=dp(2))
            b.add_widget(make_label(
                lbl, size=11,
                color=DIM, height=22))
            b.add_widget(widget)
            return b

        self.cc_type  = make_spinner(
            ['BUY','SELL'])
        self.cc_qty   = make_input(
            'Quantity e.g. 100',
            input_filter='int')
        self.cc_price = make_input(
            'Price e.g. 1000',
            input_filter='float')
        self.cc_bprice= make_input(
            'Buy Price (for sell analysis)',
            input_filter='float')
        self.cc_days  = make_input(
            'Holding Days e.g. 180',
            '180', input_filter='int')
        self.cc_t1    = make_input(
            'Target 1 %', '10',
            input_filter='float')
        self.cc_t2    = make_input(
            'Target 2 %', '20',
            input_filter='float')
        self.cc_t3    = make_input(
            'Target 3 %', '30',
            input_filter='float')

        form.add_widget(field(
            'Type', self.cc_type))
        form.add_widget(field(
            'Quantity', self.cc_qty))
        form.add_widget(field(
            'Price/Share', self.cc_price))
        form.add_widget(field(
            'Buy Price (sell analysis)',
            self.cc_bprice))
        form.add_widget(field(
            'Days Held', self.cc_days))
        form.add_widget(field(
            'Target 1 %', self.cc_t1))
        form.add_widget(field(
            'Target 2 %', self.cc_t2))
        form.add_widget(field(
            'Target 3 %', self.cc_t3))

        form.add_widget(make_button(
            '🔢 Calculate All',
            self._calc, bg=ORANGE,
            height=50))

        self.result = Label(
            text='Fill above and Calculate',
            font_size=sp(11),
            color=GREEN,
            markup=True,
            halign='left',
            size_hint_y=None,
            height=dp(10))
        self.result.bind(
            size=lambda i, v:
            setattr(i, 'text_size',
                    (v[0], None)),
            texture_size=lambda i, v:
            setattr(i, 'height',
                    v[1] + dp(20)))

        form.add_widget(self.result)
        sv.add_widget(form)

        nav = make_nav(
            self.manager, 'calc')

        root.add_widget(hdr)
        root.add_widget(sv)
        root.add_widget(nav)
        self.add_widget(root)

    def _calc(self):
        try:
            ttype = self.cc_type.text
            qty   = int(
                self.cc_qty.text or '100')
            price = float(
                self.cc_price.text or '1000')
            days  = int(
                self.cc_days.text or '180')
            t1 = float(
                self.cc_t1.text or '10')
            t2 = float(
                self.cc_t2.text or '20')
            t3 = float(
                self.cc_t3.text or '30')

            S = '─'*34
            L = [f'[b]{"═"*34}[/b]']

            if ttype == 'BUY':
                c = Calc.buy(qty, price)
                L += [
                    f'[b]BUY'
                    f' {qty:,} × Rs {price:,.2f}[/b]',
                    S,
                    f'Gross  Rs {c["gross"]:>12,.2f}',
                    f'Broker Rs {c["broker"]:>12,.2f}',
                    f'SEBON  Rs {c["sebon"]:>12,.2f}',
                    f'DP     Rs {c["dp"]:>12.2f}',
                    f'CM Fee Rs {c["cm"]:>12,.2f}',
                    S,
                    f'Total  Rs {c["charges"]:>12,.2f}',
                    f'[b]NET    Rs {c["net"]:>12,.2f}[/b]',
                    f'[b]WACC   Rs {c["wacc"]:>12,.2f}[/b]',
                    '',
                    f'[b]TARGET SELL PRICES:[/b]',
                    S,
                ]
                bd = str(
                    datetime.date.today()
                    - datetime.timedelta(
                        days=days))
                cr  = (Calc.CGT_S
                       if days <= 365
                       else Calc.CGT_L)
                crt = ('7.5%'
                       if days <= 365
                       else '10%')
                for pct in [t1, t2, t3]:
                    tp  = Calc.target(
                        c['wacc'], qty,
                        bd, pct)
                    sc  = Calc.sell(qty, tp)
                    gp  = qty*tp - c['net']
                    ca  = (gp * cr
                           if gp > 0 else 0)
                    np_ = (gp
                           - sc['charges']
                           - ca)
                    L += [
                        f'[b]{pct:.0f}% Net:[/b]'
                        f' Rs {tp:,.2f}',
                        f'  Sell: Rs {sc["charges"]:,.2f}'
                        f'  CGT({crt}): Rs {ca:,.2f}',
                        f'  [b]Net: Rs {np_:,.2f}[/b]',
                        '',
                    ]
            else:
                c = Calc.sell(qty, price)
                L += [
                    f'[b]SELL'
                    f' {qty:,} × Rs {price:,.2f}[/b]',
                    S,
                    f'Gross  Rs {c["gross"]:>12,.2f}',
                    f'Broker Rs {c["broker"]:>12,.2f}',
                    f'SEBON  Rs {c["sebon"]:>12,.2f}',
                    f'DP     Rs {c["dp"]:>12.2f}',
                    S,
                    f'Total  Rs {c["charges"]:>12,.2f}',
                    f'[b]NET    Rs {c["net"]:>12,.2f}[/b]',
                ]
                bp = self.cc_bprice.text
                if bp:
                    bpr = float(bp)
                    bc  = Calc.buy(qty, bpr)
                    bd  = str(
                        datetime.date.today()
                        - datetime.timedelta(
                            days=days))
                    pft = c['net'] - bc['net']
                    ca, cl = Calc.cgt(pft, bd)
                    np_ = pft - ca
                    nr  = (np_/bc['net']*100
                           if bc['net'] else 0)
                    L += [
                        '',
                        f'[b]PROFIT:[/b]',
                        S,
                        f'Buy cost Rs {bc["net"]:>10,.2f}',
                        f'Gross P/L Rs {pft:>9,.2f}',
                        f'CGT ({cl}) Rs {ca:>9,.2f}',
                        f'[b]Net Rs {np_:>12,.2f}[/b]',
                        f'Return: {nr:.2f}%',
                    ]

            L.append(f'[b]{"═"*34}[/b]')
            self.result.text = '\n'.join(L)

        except (ValueError, TypeError):
            self.result.text = (
                '⚠️ Enter valid numbers!')


# ════════════════════════════════════════════════
# SCREEN: BONUS / RIGHTS / DIVIDEND
# ════════════════════════════════════════════════
class BonusScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name='bonus', **kw)
        self.db   = DB.get()
        self.port = Portfolio()
        self._built = False

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True

    def _build(self):
        root = BoxLayout(
            orientation='vertical')
        set_bg(root, BG)

        hdr = make_label(
            '🎁 Bonus / Rights / Dividend',
            size=14, bold=True,
            color=PURPLE, height=46,
            halign='center')

        sv = ScrollView(
            do_scroll_x=False)
        form = GridLayout(
            cols=1, spacing=dp(5),
            padding=dp(10),
            size_hint_y=None)
        form.bind(
            minimum_height=
            form.setter('height'))

        def field(lbl, widget):
            b = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=dp(75),
                spacing=dp(2))
            b.add_widget(make_label(
                lbl, size=11,
                color=DIM, height=22))
            b.add_widget(widget)
            return b

        # Help text
        help_card = BoxLayout(
            size_hint_y=None,
            height=dp(90),
            padding=dp(8))
        set_card_bg(help_card, CARD2)
        help_card.add_widget(make_label(
            'BONUS: Rate = bonus%, e.g. 20\n'
            'RIGHTS: Rate = shares per 1 right,'
            ' e.g. 5\n'
            'CASH DIV: Rate = dividend%, e.g. 25\n'
            'SPLIT: Rate = multiple, e.g. 10',
            size=10, color=YELLOW,
            height=84))
        form.add_widget(help_card)

        self.ca_type = make_spinner([
            'BONUS', 'RIGHTS',
            'CASH_DIVIDEND', 'STOCK_SPLIT'])
        self.ca_sym  = make_input(
            'Symbol e.g. NABIL')
        self.ca_date = make_input(
            'Date YYYY-MM-DD',
            str(datetime.date.today()))
        self.ca_rate = make_input(
            'Rate / % / Ratio',
            input_filter='float')
        self.ca_rp   = make_input(
            'Rights Price Rs',
            '100', input_filter='float')
        self.ca_shr  = make_input(
            'Shares on Record Date',
            input_filter='int')

        form.add_widget(field(
            'Action Type', self.ca_type))
        form.add_widget(field(
            'Symbol', self.ca_sym))
        form.add_widget(field(
            'Date', self.ca_date))
        form.add_widget(field(
            'Rate / %', self.ca_rate))
        form.add_widget(field(
            'Rights Price', self.ca_rp))
        form.add_widget(field(
            'Shares Held', self.ca_shr))

        form.add_widget(make_button(
            '✅ Process Action',
            self._process,
            bg=GREEN, height=50))

        self.result = Label(
            text='Select action and fill details',
            font_size=sp(11),
            color=YELLOW,
            markup=True,
            halign='left',
            size_hint_y=None,
            height=dp(10))
        self.result.bind(
            size=lambda i, v:
            setattr(i, 'text_size',
                    (v[0], None)),
            texture_size=lambda i, v:
            setattr(i, 'height',
                    v[1] + dp(20)))
        form.add_widget(self.result)
        sv.add_widget(form)

        nav = make_nav(
            self.manager, 'bonus')

        root.add_widget(hdr)
        root.add_widget(sv)
        root.add_widget(nav)
        self.add_widget(root)

    def _process(self):
        try:
            atype = self.ca_type.text
            sym   = (self.ca_sym.text
                     .upper().strip())
            date  = self.ca_date.text.strip()
            rate  = float(
                self.ca_rate.text or '0')
            rp    = float(
                self.ca_rp.text or '100')
            shr   = int(
                self.ca_shr.text or '0')

            if not sym or not date:
                self.result.text = (
                    '❌ Symbol & Date needed!')
                return

            h = self.port.holding(sym)

            if atype == 'BONUS':
                if not h:
                    self.result.text = (
                        f'❌ No holding: {sym}')
                    return
                ns   = int(shr * rate / 100)
                ow   = h['wacc']
                otc  = h['tc']
                ntot = h['cq'] + ns
                nw   = otc / ntot
                self.db.run('''
                    INSERT INTO transactions
                    (trans_date,symbol,
                     company_name,trans_type,
                     quantity,price_per_share,
                     gross_amount,net_amount,
                     broker_name,notes)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                ''', (date,sym,h['company'],
                      'BUY',ns,0,0,0,
                      'BONUS',
                      f'{rate}% bonus'))
                self.db.run('''
                    INSERT INTO corp_actions
                    (action_date,symbol,
                     action_type,details,
                     new_shares)
                    VALUES(?,?,?,?,?)
                ''', (date,sym,'BONUS',
                      f'{rate}% bonus',ns))
                self.result.text = (
                    f'✅ [b]BONUS DONE![/b]\n'
                    f'{"═"*28}\n'
                    f'Symbol    : {sym}\n'
                    f'Bonus     : {rate}%\n'
                    f'New Shares: {ns:,}\n'
                    f'Before    : {h["cq"]:,}\n'
                    f'After     : {ntot:,}\n'
                    f'Old WACC  : Rs {ow:,.2f}\n'
                    f'New WACC  : Rs {nw:,.2f}\n'
                    f'Cost same : Rs {otc:,.2f}'
                )

            elif atype == 'RIGHTS':
                if not h:
                    self.result.text = (
                        f'❌ No holding: {sym}')
                    return
                rs  = int(shr / rate)
                rc  = Calc.buy(rs, rp)
                ow  = h['wacc']
                ntc = h['tc'] + rc['net']
                ntot= h['cq'] + rs
                nw  = ntc / ntot
                self.db.run('''
                    INSERT INTO transactions
                    (trans_date,symbol,
                     company_name,trans_type,
                     quantity,price_per_share,
                     gross_amount,
                     broker_commission,
                     sebon_fee,dp_charge,
                     capital_market_fee,
                     total_charges,net_amount,
                     broker_name,notes)
                    VALUES(?,?,?,?,?,?,?,?,
                           ?,?,?,?,?,?,?)
                ''', (date,sym,h['company'],
                      'BUY',rs,rp,
                      rc['gross'],rc['broker'],
                      rc['sebon'],rc['dp'],
                      rc['cm'],rc['charges'],
                      rc['net'],'RIGHTS',
                      f'1:{int(rate)} @Rs{rp}'))
                self.result.text = (
                    f'✅ [b]RIGHTS DONE![/b]\n'
                    f'{"═"*28}\n'
                    f'Symbol    : {sym}\n'
                    f'Ratio     : 1:{int(rate)}\n'
                    f'Price     : Rs {rp:,.2f}\n'
                    f'Shares Rxd: {rs:,}\n'
                    f'Cost      : Rs {rc["net"]:,.2f}\n'
                    f'Old WACC  : Rs {ow:,.2f}\n'
                    f'New WACC  : Rs {nw:,.2f}'
                )

            elif atype == 'CASH_DIVIDEND':
                par   = 100
                gross = shr * par * rate / 100
                tax   = round(
                    gross * Calc.DIV_TAX, 2)
                net   = gross - tax
                self.db.run('''
                    INSERT INTO dividends
                    (record_date,symbol,
                     div_type,rate,
                     gross,tax,net,notes)
                    VALUES(?,?,?,?,?,?,?,?)
                ''', (date,sym,'CASH',
                      rate,gross,tax,net,
                      f'{rate}% dividend'))
                self.result.text = (
                    f'✅ [b]DIVIDEND SAVED![/b]\n'
                    f'{"═"*28}\n'
                    f'Symbol    : {sym}\n'
                    f'Rate      : {rate}%\n'
                    f'Shares    : {shr:,}\n'
                    f'Gross     : Rs {gross:,.2f}\n'
                    f'TDS (5%)  : Rs {tax:,.2f}\n'
                    f'Net Rxd   : Rs {net:,.2f}'
                )

            elif atype == 'STOCK_SPLIT':
                if not h:
                    self.result.text = (
                        f'❌ No holding: {sym}')
                    return
                add = int(h['cq']*(rate-1))
                ow  = h['wacc']
                nw  = (ow/rate if rate else ow)
                self.db.run('''
                    INSERT INTO transactions
                    (trans_date,symbol,
                     company_name,trans_type,
                     quantity,price_per_share,
                     gross_amount,net_amount,
                     broker_name,notes)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                ''', (date,sym,h['company'],
                      'BUY',add,0,0,0,
                      'SPLIT',
                      f'1:{int(rate)} split'))
                self.result.text = (
                    f'✅ [b]SPLIT DONE![/b]\n'
                    f'{"═"*28}\n'
                    f'Symbol    : {sym}\n'
                    f'Split     : 1:{int(rate)}\n'
                    f'Old Shares: {h["cq"]:,}\n'
                    f'New Total : {h["cq"]+add:,}\n'
                    f'Old WACC  : Rs {ow:,.2f}\n'
                    f'New WACC  : Rs {nw:,.2f}'
                )

        except (ValueError, TypeError):
            self.result.text = (
                '❌ Enter valid numbers!')
        except Exception as e:
            self.result.text = (
                f'❌ Error: {str(e)}')


# ════════════════════════════════════════════════
# SCREEN: HISTORY
# ════════════════════════════════════════════════
class HistoryScreen(Screen):
    def __init__(self, **kw):
        super().__init__(
            name='history', **kw)
        self.db = DB.get()
        self._built = False

    def on_enter(self):
        if not self._built:
            self._build()
            self._built = True
        self._update()

    def _build(self):
        root = BoxLayout(
            orientation='vertical')
        set_bg(root, BG)

        hdr = make_label(
            '📋 History',
            size=15, bold=True,
            color=BLUE, height=46,
            halign='center')

        sv = ScrollView(
            do_scroll_x=False)
        self.hist_box = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(5),
            padding=dp(8))
        self.hist_box.bind(
            minimum_height=
            self.hist_box.setter('height'))
        sv.add_widget(self.hist_box)

        nav = make_nav(
            self.manager, 'history')

        root.add_widget(hdr)
        root.add_widget(sv)
        root.add_widget(nav)
        self.add_widget(root)

    def _update(self):
        self.hist_box.clear_widgets()
        txns = self.db.all(
            'SELECT * FROM transactions'
            ' ORDER BY trans_date DESC,'
            ' id DESC LIMIT 60')

        if not txns:
            self.hist_box.add_widget(
                make_label(
                    '  No transactions yet.',
                    size=13, color=DIM,
                    height=80))
            return

        for t in txns:
            is_buy = (t['trans_type'] == 'BUY')
            col    = GREEN if is_buy else RED
            icon   = '🟢' if is_buy else '🔴'

            card = BoxLayout(
                size_hint_y=None,
                height=dp(72),
                padding=dp(10))
            set_card_bg(card, CARD, 6)

            txt = (
                f"[b]{icon}"
                f" {t['trans_type']}"
                f"  {t['symbol']}[/b]"
                f"  {t['trans_date']}\n"
                f"Qty: {t['quantity']:,}"
                f" × Rs {t['price_per_share']:,.2f}"
                f"  Gross:"
                f" Rs {t['gross_amount']:,.2f}\n"
                f"Charges:"
                f" Rs {t['total_charges']:,.2f}"
                f"  Net:"
                f" Rs {t['net_amount']:,.2f}"
            )
            lbl = Label(
                text=txt,
                font_size=sp(11),
                color=col,
                markup=True,
                halign='left',
                size_hint_y=None,
                height=dp(62))
            lbl.bind(
                size=lambda i, v:
                setattr(i, 'text_size',
                        (v[0], None)))
            card.add_widget(lbl)
            self.hist_box.add_widget(card)


# ════════════════════════════════════════════════
# MAIN APP
# ════════════════════════════════════════════════
class NEPSEApp(App):
    def build(self):
        self.title = 'NEPSE Tracker'

        # Init DB
        DB.get()

        # Screen manager
        sm = ScreenManager(
            transition=SlideTransition())

        sm.add_widget(DashScreen())
        sm.add_widget(PortScreen())
        sm.add_widget(AddScreen())
        sm.add_widget(CalcScreen())
        sm.add_widget(BonusScreen())
        sm.add_widget(HistoryScreen())

        # Auto refresh
        Clock.schedule_interval(
            self._auto, 300)

        return sm

    def _auto(self, dt):
        if Calc.is_open():
            db = DB.get()
            syms = db.all(
                'SELECT DISTINCT symbol'
                ' FROM transactions'
                ' WHERE trans_type="BUY"')
            def fetch():
                for s in syms:
                    d = Fetcher.fetch(
                        s['symbol'])
                    if d:
                        db.save_price(
                            s['symbol'], d)
            threading.Thread(
                target=fetch,
                daemon=True).start()

    def on_stop(self):
        db = DB.get()
        if db.conn:
            db.conn.close()


if __name__ == '__main__':
    NEPSEApp().run()
