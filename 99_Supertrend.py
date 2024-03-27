import pandas as pd
import pandas_ta as ta
import ssl
from urllib import request
import yfinance as yf
import matplotlib.pyplot as plt
import mplcyberpunk
import vectorbt as vbt
import numpy as np

def Hisse_Temel_Veriler():
    url1="https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx#page-1"
    context = ssl._create_unverified_context()
    response = request.urlopen(url1, context=context)
    url1 = response.read()

    df = pd.read_html(url1,decimal=',', thousands='.')                         #Tüm Hisselerin Tablolarını Aktar
    df2=df[6]
    return df2

def Supertrend(data,SENSITIVITY = 3,ATR_PERIOD = 14):
    Supertrend=data.copy()
        # UT Bot Parameters
    SENSITIVITY = 3
    ATR_PERIOD = 14
    Supertrend['xATR'] = ta.atr(data['High'], data['Low'], data['Adj Close'], timeperiod=ATR_PERIOD)
    Supertrend['nLoss'] = SENSITIVITY * Supertrend['xATR']
    Supertrend = Supertrend.dropna()
    Supertrend = Supertrend.reset_index()
    # Filling ATRTrailing Variable
    Supertrend['ATRTrailing'] = [0.0] + [np.nan for i in range(len(Supertrend) - 1)]

    for i in range(1, len(Supertrend)):
        if (Supertrend.loc[i, 'Adj Close'] > Supertrend.loc[i - 1, 'ATRTrailing']) and (Supertrend.loc[i - 1, 'Adj Close'] > Supertrend.loc[i - 1, 'ATRTrailing']):
            Supertrend.loc[i, 'ATRTrailing'] = max(Supertrend.loc[i - 1, 'ATRTrailing'],Supertrend.loc[i, 'Adj Close']-Supertrend.loc[i,'nLoss'])
        
        elif (Supertrend.loc[i, 'Adj Close'] < Supertrend.loc[i - 1, 'ATRTrailing']) and (Supertrend.loc[i - 1, 'Adj Close'] < Supertrend.loc[i - 1, 'ATRTrailing']):
            Supertrend.loc[i, 'ATRTrailing'] = min(Supertrend.loc[i - 1, 'ATRTrailing'],Supertrend.loc[i, 'Adj Close']+Supertrend.loc[i,'nLoss'])
        
        elif Supertrend.loc[i, 'Adj Close'] > Supertrend.loc[i - 1, 'ATRTrailing']:
            Supertrend.loc[i, 'ATRTrailing']=Supertrend.loc[i, 'Adj Close']-Supertrend.loc[i,'nLoss']
        else:
            Supertrend.loc[i, 'ATRTrailing']=Supertrend.loc[i, 'Adj Close']+Supertrend.loc[i,'nLoss']

    # Calculating signals
    ema = vbt.MA.run(Supertrend['Adj Close'], 1, short_name='EMA', ewm=True)
    Supertrend['Above'] = ema.ma_crossed_above(Supertrend['ATRTrailing'])
    Supertrend['Below'] = ema.ma_crossed_below(Supertrend['ATRTrailing'])
    Supertrend['Entry'] = (Supertrend['Adj Close'] > Supertrend['ATRTrailing']) & (Supertrend['Above']==True)
    Supertrend['Exit'] = (Supertrend['Adj Close'] < Supertrend['ATRTrailing']) & (Supertrend['Below']==True)
    Supertrend=Supertrend.drop(Supertrend.columns[[7,8,10,11]],axis = 1)
    return Supertrend

Hisse_Ozet=Hisse_Temel_Veriler()
Hisseler=Hisse_Ozet['Kod'].values.tolist()

Titles=['Hisse Adı','Kazanma Oranı[%]','Sharpe Oranı','Ort. Kazanma Oranı [%]','Ort Kazanma Süresi','Ort. Kayıp Oranı [%]','Ort Kayıp Süresi','Giriş Sinyali','Çıkış Sinyali']
df_signals=pd.DataFrame(columns=Titles)

for i in range(0,len(Hisseler)):
    try:
        S=3
        ATR=14
        data=yf.download(Hisseler[i]+'.IS',period='2y', interval='1d',progress=False)
        Supert=Supertrend(data,S,ATR)
        psettings = {'init_cash': 100,'freq': 'D', 'direction': 'longonly', 'accumulate': True}
        pf = vbt.Portfolio.from_signals(Supert['Adj Close'], entries=Supert['Entry'], exits=Supert['Exit'],**psettings)
        Stats=pf.stats()

        Buy=False
        Sell=False
        Signals = Supert.tail(2)
        Signals = Signals.reset_index()
        Buy = Signals.loc[0, 'Entry']==False and Signals.loc[1, 'Entry']==True
        Sell = Signals.loc[0, 'Exit']== False and Signals.loc[1, 'Exit']== True

        L1=[Hisseler[i],round(Stats.loc['Win Rate [%]'],2),round(Stats.loc['Sharpe Ratio'],2),
            round(Stats.loc['Avg Winning Trade [%]'],2),str(Stats.loc['Avg Winning Trade Duration']),
            round(Stats.loc['Avg Losing Trade [%]'],2),str(Stats.loc['Avg Losing Trade Duration']),
            str(Buy),str(Sell)]
        
        print(L1)
        df_signals.loc[len(df_signals)] = L1
        
        if Buy==True:
            pf.plot(subplots = ['orders','trades','drawdowns','trade_pnl','cum_returns']).write_image((Hisseler[i]+"_Backtest.png"))
    except:
        pass

df_True = df_signals[(df_signals['Giriş Sinyali'] == 'True') & (df_signals['Kazanma Oranı[%]'] > 50.0)]
print(df_True)