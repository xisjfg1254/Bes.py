import time, requests, os, sys, ta, threading, websocket, json
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

API_KEY = "93db075ae046407abd72cef70a825480"
TELEGRAM_TOKEN = "8419166632:AAE_MWlI3xq4NGy_04AYdRqfTNLCN5nl_yk"
CHAT_ID = "1696448892"
SYMBOL = "XAU/USD"
WS_URL = f"wss://ws.twelvedata.com/v1/quotes/price?apikey={API_KEY}"

C, G, R, Y, W, B, RST = "\033[96m", "\033[92m", "\033[91m", "\033[93m", "\033[37m", "\033[1m", "\033[0m"

HACKER_LOGO = f"""{G}
 ██████╗  ██████╗ ██╗     ██████╗      ██████╗ ██╗   ██╗ █████╗ ███╗   ██╗
██╔════╝ ██╔═══██╗██║     ██╔═══██╗    ██╔══██╗██║   ██║██╔══██╗████╗  ██║
██║  ███╗██║   ██║██║     ██║   ██║    ██║  ██║██║   ██║███████║██╔██╗ ██║
╚═════╝ ╚═════╝ ╚══════╝ ╚═════╝     ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝
{C}                    >> ELITE QUANTUM TERMINAL v6.3 <<{RST}"""

last_alerts = {"PRE": 0, "TRADE": 0}
live_price = 0.0
cached_df = None
last_fetch_time = 0

def on_message(ws, message):
    global live_price
    try:
        data = json.loads(message)
        if 'price' in data: live_price = float(data['price'])
    except: pass

def start_ws():
    ws = websocket.WebSocketApp(WS_URL, on_message=on_message, on_open=lambda ws: ws.send(json.dumps({"action": "subscribe", "params": {"symbols": SYMBOL}})))
    ws.run_forever()

threading.Thread(target=start_ws, daemon=True).start()

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
        requests.get(url, timeout=5)
    except: pass

def get_status_symbol(val):
    if val == "BUY": return f"{G}🟢 BUY{RST}"
    if val == "SELL": return f"{R}🔴 SELL{RST}"
    return f"{W}⚪ WAIT{RST}"

def draw_dashboard(mode_name, price, adx, rsi, macd, s_adx, s_rsi, s_bb, s_macd, s_ema, s_div, trend_status, status, tp_sl_data, master_plan, req_votes):
    print(HACKER_LOGO)
    
    d_adx = f"{G}🟢 STRONG{RST}" if s_adx == "STRONG" else f"{R}🔴 WEAK{RST}"
    d_rsi = get_status_symbol(s_rsi)
    d_bb  = get_status_symbol(s_bb)
    d_macd = get_status_symbol(s_macd)
    d_trend = f"{G}🟢 BULLISH{RST}" if trend_status == "BULLISH" else f"{R}🔴 BEARISH{RST}"
    d_ema = get_status_symbol(s_ema)
    d_div = f"{G}🟢 BULL_DIV{RST}" if s_div == "BULLISH" else (f"{R}🔴 BEAR_DIV{RST}" if s_div == "BEARISH" else f"{W}⚪ NONE{RST}")
    
    def format_detailed(key):
        entry, tp, sl = tp_sl_data.get(key, (0,0,0))
        if entry == 0: return f"{W}E:  ---  TP:  ---  SL:  --- "
        return f"{W}E:{entry:>6.1f} {G}TP:{tp:>6.1f} {R}SL:{sl:>6.1f}"

    print(f"{C}┌─────────────────────────────────────────────────────────────┐")
    print(f"{C}│ {W}MODE : {B}{mode_name:<30} {W}REQ:{Y}{req_votes}/6{C} │")
    print(f"{C}├─────────────────────────────────────────────────────────────┤")
    print(f"{C}│ {W}Market Price : {G}{price:,.2f}{C}{'':<33} │")
    print(f"{C}│ {W}Trend (EMA200): {d_trend:<23} {C} │")
    print(f"{C}│ {W}ADX  (Strength): {adx:>6.2f} [{d_adx:<12}] {format_detailed('ADX')} │")
    print(f"{C}│ {W}RSI  (Momentum): {rsi:>6.2f} [{d_rsi:<12}] {format_detailed('RSI')} │")
    print(f"{C}│ {W}MACD (Trend)  : {macd:>6.2f} [{d_macd:<12}] {format_detailed('MACD')} │")
    print(f"{C}│ {W}EMA  (Filter) : {d_ema:<22} {format_detailed('EMA')} │")
    print(f"{C}│ {W}DIVERGENCE  : {d_div:<22} {C} │")
    print(f"{C}│ {W}BB   (Status) : {d_bb:<22} {format_detailed('BB')} │")
    print(f"{C}├─────────────────────────────────────────────────────────────┤")
    print(f"{C}│ {W}Status        : {Y}{status:<43}{C} │")
    if master_plan:
        e, t, s = master_plan
        print(f"{C}│ {W}MASTER SIGNAL : {W}E:{e:.2f} {G}TP:{t:.2f} {R}SL:{s:.2f}{'':<4} {C}│")
    print(f"{C}└─────────────────────────────────────────────────────────────┘{RST}")

def get_data(interval):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={interval}&outputsize=250&apikey={API_KEY}"
        response = requests.get(url, timeout=5)
        data = response.json()
        if 'values' not in data: return None
        df = pd.DataFrame(data['values']).iloc[::-1].reset_index(drop=True)
        df[['high', 'low', 'close']] = df[['high', 'low', 'close']].astype(float)
        return df
    except: return None

def check_divergence(df, rsi_series):
    if len(df) < 10: return "NONE"
    price_low = df['low'].iloc[-5:].min(); price_high = df['high'].iloc[-5:].max()
    rsi_low = rsi_series.iloc[-5:].min(); rsi_high = rsi_series.iloc[-5:].max()
    if df['close'].iloc[-1] < price_low and rsi_series.iloc[-1] > rsi_low: return "BULLISH"
    elif df['close'].iloc[-1] > price_high and rsi_series.iloc[-1] < rsi_high: return "BEARISH"
    return "NONE"

print(f"{G}Select Mode: [1] 1min, [2] 5min, [3] 15min")
choice = input(f"{C}Mode number: {RST}")
mode = {"1": {"name": "ULTRA SCALPING (1min)", "tf": "1min", "adx": 30},
        "2": {"name": "PRO SCALPING (5min)", "tf": "5min", "adx": 25},
        "3": {"name": "SWING TRADING (15min)", "tf": "15min", "adx": 20}}.get(choice, {"name": "PRO SCALPING (5min)", "tf": "5min", "adx": 25})

while True:
    if live_price == 0: time.sleep(1); continue 
    
    if time.time() - last_fetch_time > 60:
        new_df = get_data(mode['tf'])
        if new_df is not None:
            cached_df = new_df
            last_fetch_time = time.time()
            
    if cached_df is None: time.sleep(1); continue

    df = cached_df.copy()
    df.loc[df.index[-1], 'close'] = live_price
    price = live_price
    
    rsi_series = ta.momentum.rsi(df['close'], window=14)
    rsi_val = rsi_series.iloc[-1]
    adx_val = ta.trend.adx(df['high'], df['low'], df['close'], window=14).iloc[-1]
    ema200 = ta.trend.ema_indicator(df['close'], window=200).iloc[-1]
    macd_ind = ta.trend.MACD(df['close'])
    macd_val = macd_ind.macd().iloc[-1]
    macd_sig = macd_ind.macd_signal().iloc[-1]
    atr = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14).iloc[-1]
    bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=3.5)
    
    trend_status = "BULLISH" if price > ema200 else "BEARISH"
    
    # المؤشرات
    s_bb = "BUY" if price <= bb.bollinger_lband().iloc[-1] else ("SELL" if price >= bb.bollinger_hband().iloc[-1] else "WAIT")
    s_rsi = "BUY" if rsi_val < 35 else ("SELL" if rsi_val > 65 else "WAIT")
    s_macd = "BUY" if macd_val > macd_sig else "SELL"
    s_ema = "BUY" if price > ema200 else "SELL"
    s_adx = "STRONG" if adx_val > mode['adx'] else "WEAK"
    s_div = check_divergence(df, rsi_series)
    
    s_adx_vote = "BUY" if (s_adx == "STRONG" and trend_status == "BULLISH") else ("SELL" if (s_adx == "STRONG" and trend_status == "BEARISH") else "WAIT")
    s_div_vote = "BUY" if s_div == "BULLISH" else ("SELL" if s_div == "BEARISH" else "WAIT")
    
    # دالة مساعدة لتوليد البيانات فقط عند الحاجة
    def calc_tp_sl(status, side_multiplier=2.0):
        if status == "BUY": return (price, price + (atr * side_multiplier), price - (atr * 1.0))
        if status == "SELL": return (price, price - (atr * side_multiplier), price + (atr * 1.0))
        return (0, 0, 0)

    # حساب البيانات (الآن فارغة في حالة WAIT)
    tp_sl_data = {
        "ADX": calc_tp_sl(s_adx_vote, 1.5),
        "BB": calc_tp_sl(s_bb, 2.5),
        "RSI": calc_tp_sl(s_rsi, 2.0),
        "MACD": calc_tp_sl(s_macd, 1.5),
        "EMA": calc_tp_sl(s_ema, 1.0)
    }
    
    required_votes = 5 if adx_val > 50 else 4
    
    directional_signals = [s_bb, s_rsi, s_macd, s_ema, s_adx_vote, s_div_vote]
    buy_votes = directional_signals.count("BUY")
    sell_votes = directional_signals.count("SELL")
    
    master_plan = None
    status = f"SCANNING ({buy_votes+sell_votes}/6)..."
    
    if buy_votes >= required_votes:
        status = f"!!! BUY SIGNAL ({buy_votes}/6) !!!"
        master_plan = (price, price + (atr * 2.5), price - (atr * 1.5))
        if time.time() - last_alerts["TRADE"] > 300:
            send_telegram(f"🟢 BUY CONFIRMED! ({buy_votes}/6) Price: {price:.2f}"); last_alerts["TRADE"] = time.time()
    elif sell_votes >= required_votes:
        status = f"!!! SELL SIGNAL ({sell_votes}/6) !!!"
        master_plan = (price, price - (atr * 2.5), price + (atr * 1.5))
        if time.time() - last_alerts["TRADE"] > 300:
            send_telegram(f"🔴 SELL CONFIRMED! ({sell_votes}/6) Price: {price:.2f}"); last_alerts["TRADE"] = time.time()
    else:
        if buy_votes > sell_votes: status = f"POTENTIAL BUY ({buy_votes}/6)"
        elif sell_votes > buy_votes: status = f"POTENTIAL SELL ({sell_votes}/6)"

    draw_dashboard(mode['name'], price, adx_val, rsi_val, macd_val, s_adx, s_rsi, s_bb, s_macd, s_ema, s_div, trend_status, status, tp_sl_data, master_plan, required_votes)
    time.sleep(0.5)