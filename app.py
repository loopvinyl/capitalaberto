# ==============================================================
# 📊 APP CAPITAL ABERTO – ANÁLISE COMPLETA DE DEMONSTRAÇÕES FINANCEIRAS
# Base: capitalaberto.xlsx (gerado pelo script único)
# ==============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
import yfinance as yf
from datetime import datetime, timedelta, date, timezone
import locale
import time
import re

# ==============================
# CORREÇÃO PARA STREAMLIT CLOUD
# ==============================
import appdirs as ad
from pathlib import Path
from curl_cffi import requests as curl_requests
import tempfile

CACHE_DIR = os.path.join(tempfile.gettempdir(), "yf_cache")
ad.user_cache_dir = lambda *args: CACHE_DIR
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
# ==============================

# ==============================
# FUNÇÃO DE HORÁRIO DE BRASÍLIA (UTC-3)
# ==============================
def agora_brasil():
    """Retorna o datetime atual no fuso horário de Brasília (UTC-3), sem timezone para compatibilidade."""
    return (datetime.now(timezone.utc) - timedelta(hours=3)).replace(tzinfo=None)

# ==============================
# FUNÇÃO PARA VERIFICAR SE A B3 ESTÁ ABERTA
# ==============================
def bolsa_aberta_agora():
    """Verifica se a B3 está aberta no momento (dias úteis, 10h às 17h, horário de Brasília)."""
    agora = agora_brasil()
    if agora.weekday() >= 5:
        return False
    return 10 <= agora.hour < 17

# ==============================
# CONFIGURAÇÃO DE FORMATAÇÃO BRASILEIRA
# ==============================
def configurar_locale_brasil():
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
        except:
            pass
configurar_locale_brasil()

# ==============================
# FUNÇÕES DE FORMATAÇÃO
# ==============================
def formatar_moeda_brasil_correta(valor, casas_decimais=2):
    if valor is None or pd.isna(valor):
        return "R$ -"
    try:
        valor_em_reais = valor * 1000
        if abs(valor_em_reais) >= 1e12:
            return f"R$ {valor_em_reais/1e12:,.{casas_decimais}f} tri".replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(valor_em_reais) >= 1e9:
            return f"R$ {valor_em_reais/1e9:,.{casas_decimais}f} bi".replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(valor_em_reais) >= 1e6:
            return f"R$ {valor_em_reais/1e6:,.{casas_decimais}f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            return f"R$ {valor_em_reais/1e3:,.0f} mil".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return f"R$ {valor}"

def formatar_numero_brasil_correto(valor, casas_decimais=0):
    if valor is None or pd.isna(valor):
        return "N/A"
    try:
        if abs(valor) >= 1e12:
            return f"{valor/1e12:,.{casas_decimais}f} tri".replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(valor) >= 1e9:
            return f"{valor/1e9:,.{casas_decimais}f} bi".replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(valor) >= 1e6:
            return f"{valor/1e6:,.{casas_decimais}f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
        elif casas_decimais == 0:
            return f"{valor:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            return f"{valor:,.{casas_decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)

def formatar_percentual_brasil(valor, casas_decimais=2):
    if valor is None or pd.isna(valor):
        return "Não reportado"
    try:
        return f"{valor:.{casas_decimais}%}".replace(".", ",")
    except:
        return str(valor)

def formatar_dataframe_percentual(df, colunas):
    df_formatado = df.copy()
    for coluna in colunas:
        if coluna in df_formatado.columns:
            df_formatado[coluna] = df_formatado[coluna].apply(
                lambda x: formatar_percentual_brasil(x, 2) if pd.notna(x) else "Não reportado"
            )
    return df_formatado

# ==============================
# FUNÇÃO PARA DESCOBRIR O TICKER CORRETO NO YAHOO
# ==============================
@st.cache_data(ttl=3600)
def _obter_ticker_yahoo_interno(ticker_base):
    ticker_base = str(ticker_base).strip().upper()

    if re.search(r'\d+$', ticker_base):
        return f"{ticker_base}.SA"

    base = re.sub(r'\d+$', '', ticker_base).upper()
    sufixos = ['3', '4', '5', '6', '11']
    session = curl_requests.Session(impersonate="chrome")

    for suf in sufixos:
        ticker_yf = f"{base}{suf}.SA"
        try:
            acao = yf.Ticker(ticker_yf, session=session)
            hist = acao.history(period="5d")
            if not hist.empty:
                return ticker_yf
        except Exception:
            pass

    raise RuntimeError(f"Ticker não encontrado para {ticker_base}")

def obter_ticker_yahoo(ticker_base):
    try:
        return _obter_ticker_yahoo_interno(ticker_base)
    except Exception:
        base = re.sub(r'\d+$', '', str(ticker_base).strip().upper())
        return f"{base}.SA"

# ==============================
# FUNÇÕES DE MERCADO E DIVIDENDOS (com cache, curl_cffi e horário de Brasília)
# ==============================
def _buscar_cotacao_interna(ticker):
    ticker_yf = obter_ticker_yahoo(ticker)
    session = curl_requests.Session(impersonate="chrome")
    acao = yf.Ticker(ticker_yf, session=session)

    cotacao = None
    info = {}

    # 1) fast_info
    try:
        fi = acao.fast_info
        for chave in ("last_price", "lastPrice", "regular_market_price", "regularMarketPrice"):
            try:
                v = fi.get(chave) if hasattr(fi, "get") else getattr(fi, chave, None)
            except Exception:
                v = None
            if v and float(v) > 0:
                cotacao = float(v)
                break
    except Exception:
        pass

    # 2) .info
    try:
        info = acao.info or {}
    except Exception:
        info = {}

    if not cotacao or cotacao <= 0:
        for chave in ("regularMarketPrice", "currentPrice",
                      "regularMarketPreviousClose", "previousClose"):
            v = info.get(chave)
            if v and float(v) > 0:
                cotacao = float(v)
                break

    # 3) history
    if not cotacao or cotacao <= 0:
        try:
            hist = acao.history(period="5d")
            if not hist.empty:
                fechamentos = hist["Close"].dropna()
                if not fechamentos.empty:
                    ultimo = float(fechamentos.iloc[-1])
                    if ultimo > 0:
                        cotacao = ultimo
        except Exception:
            pass

    if not cotacao or cotacao <= 0:
        raise RuntimeError(f"Sem cotação para {ticker} ({ticker_yf})")

    return {
        'cotacao': cotacao,
        'mercado_aberto': bolsa_aberta_agora(),
        'moeda': info.get('currency', 'BRL'),
        'nome': info.get('longName', ticker),
        'setor': info.get('sector', 'N/A'),
        'industria': info.get('industry', 'N/A'),
        'market_cap': info.get('marketCap'),
        'sharesOutstanding': info.get('sharesOutstanding'),
        'volume': info.get('volume'),
        'data_atualizacao': agora_brasil().strftime("%d/%m/%Y %H:%M")
    }

@st.cache_data(ttl=900)
def _buscar_cotacao_cached(ticker):
    return _buscar_cotacao_interna(ticker)

def buscar_cotacao_atual(ticker):
    try:
        return _buscar_cotacao_cached(ticker)
    except Exception:
        return None

@st.cache_data(ttl=3600)
def buscar_dividendos_historicos(ticker):
    try:
        ticker_yf = obter_ticker_yahoo(ticker)
        session = curl_requests.Session(impersonate="chrome")
        acao = yf.Ticker(ticker_yf, session=session)
        dividendos = acao.dividends
        if dividendos.empty:
            return None
        df_div = dividendos.reset_index()
        df_div.columns = ['Data', 'Dividendo']
        df_div['Data'] = df_div['Data'].dt.tz_localize(None)
        df_div = df_div[df_div['Data'] >= datetime(2010, 1, 1)]
        df_div['Ano'] = df_div['Data'].dt.year
        df_div['Mes'] = df_div['Data'].dt.month
        df_div = df_div.sort_values('Data')
        return df_div
    except:
        return None

@st.cache_data(ttl=3600)
def buscar_historico_precos(ticker, periodo_maximo="max"):
    try:
        ticker_yf = obter_ticker_yahoo(ticker)
        session = curl_requests.Session(impersonate="chrome")
        acao = yf.Ticker(ticker_yf, session=session)
        historico = acao.history(period=periodo_maximo)
        if historico.empty:
            return None
        historico.index = historico.index.tz_localize(None)
        return historico
    except:
        return None

def calcular_estatisticas_dividendos(df_dividendos):
    if df_dividendos is None or df_dividendos.empty:
        return None
    return {
        'total_dividendos': df_dividendos['Dividendo'].sum(),
        'media_anual': df_dividendos.groupby('Ano')['Dividendo'].sum().mean(),
        'maior_dividendo': df_dividendos['Dividendo'].max(),
        'menor_dividendo': df_dividendos['Dividendo'].min(),
        'frequencia_media': len(df_dividendos) / df_dividendos['Ano'].nunique(),
        'ultimo_dividendo': df_dividendos.iloc[-1]['Dividendo'] if len(df_dividendos) > 0 else 0,
        'data_ultimo': df_dividendos.iloc[-1]['Data'] if len(df_dividendos) > 0 else None
    }

def calcular_tickers_consistentes(df_cvm, anos_verificar=5, minimo_anos_com_pagamento=3):
    st.info(f"🔎 **Pré‑filtro:** Buscando tickers com pagamento de dividendos em pelo menos {minimo_anos_com_pagamento} dos últimos {anos_verificar} anos.")

    anos_disponiveis = sorted(df_cvm['Ano'].unique(), reverse=True)
    ultimos_anos = anos_disponiveis[:anos_verificar]
    tickers_validos = df_cvm['Ticker'].unique()
    tickers_consistentes = []

    progress_bar = st.progress(0, text="Verificando consistência de dividendos...")
    for i, ticker in enumerate(tickers_validos):
        df_ticker = df_cvm[(df_cvm['Ticker'] == ticker) & (df_cvm['Ano'].isin(ultimos_anos))]
        if 'Pagamento de Dividendos' not in df_ticker.columns:
            continue

        pagamentos = df_ticker[df_ticker['Pagamento de Dividendos'].notna() & (df_ticker['Pagamento de Dividendos'] != 0)]
        anos_com_pagamento = pagamentos['Ano'].nunique()

        if anos_com_pagamento >= minimo_anos_com_pagamento:
            tickers_consistentes.append(ticker)

        progress_bar.progress((i+1)/len(tickers_validos), text=f"Verificando {ticker} ({i+1}/{len(tickers_validos)})...")

    progress_bar.empty()
    st.success(f"✅ {len(tickers_consistentes)} tickers com pagamento consistente (≥ {minimo_anos_com_pagamento} anos nos últimos {anos_verificar}).")
    return tickers_consistentes

def calcular_ranking_dividendos(tickers_consistentes, df_cvm, periodo_dy_anos=10):
    dados_ranking = []
    if not tickers_consistentes:
        return pd.DataFrame()

    ano_recente = df_cvm['Ano'].max()
    setor_map = df_cvm[df_cvm['Ano'] == ano_recente][['Ticker', 'SETOR_ATIV']].drop_duplicates(subset=['Ticker'])
    setor_map = setor_map.set_index('Ticker')['SETOR_ATIV'].to_dict()

    st.warning(f"⚠️ Calculando DY médio de {periodo_dy_anos} anos para {len(tickers_consistentes)} tickers.")
    progress_bar = st.progress(0, text="Buscando dados de mercado...")

    for i, ticker in enumerate(tickers_consistentes):
        dados_cotacao = buscar_cotacao_atual(ticker)
        data_inicio = agora_brasil() - timedelta(days=365 * periodo_dy_anos)
        df_precos = buscar_historico_precos(ticker, "max")
        df_div = buscar_dividendos_historicos(ticker)
        dy_medio = None

        if dados_cotacao and df_precos is not None and df_div is not None and not df_div.empty:
            df_precos_filt = df_precos[df_precos.index >= data_inicio]
            df_div_filt = df_div[df_div['Data'] >= data_inicio]
            if not df_precos_filt.empty and not df_div_filt.empty:
                try:
                    precos_anuais = df_precos_filt.resample('YE').last()['Close'].dropna()
                except:
                    try:
                        precos_anuais = df_precos_filt.resample('A').last()['Close'].dropna()
                    except:
                        precos_anuais = pd.Series(dtype=float)
                df_div_anual = df_div_filt.groupby(df_div_filt['Data'].dt.year)['Dividendo'].sum()
                dy_anuais = []
                for ano, dividendo_total in df_div_anual.items():
                    if ano in precos_anuais.index.year:
                        preco_final = precos_anuais[precos_anuais.index.year == ano].iloc[0]
                        if preco_final > 0:
                            dy_anuais.append((dividendo_total / preco_final) * 100)
                if dy_anuais:
                    dy_medio = np.mean(dy_anuais)

        if dados_cotacao is not None:
            setor = setor_map.get(ticker, dados_cotacao.get('setor', 'N/A'))
            dados_ranking.append({
                'Ticker': ticker,
                'Setor': setor,
                'Cotação Atual': dados_cotacao['cotacao'],
                f'DY Médio ({periodo_dy_anos}A)': dy_medio
            })
        time.sleep(0.5)
        progress_bar.progress((i+1)/len(tickers_consistentes), text=f"Buscando {ticker} ({i+1}/{len(tickers_consistentes)})...")

    progress_bar.empty()
    return pd.DataFrame(dados_ranking).fillna(0)

@st.cache_data(ttl=3600, show_spinner=False)
def calcular_ranking_retorno_total(tickers_validos, data_inicio, valor_investido_inicial):
    dados_ranking = []
    st.info(f"⏳ Calculando ranking de retorno total para {len(tickers_validos)} tickers. Aguarde...")
    progress_bar = st.progress(0, text="Iniciando simulação...")
    for i, ticker in enumerate(tickers_validos):
        resultado = simular_investimento_valor(ticker, data_inicio, valor_investido_inicial)
        if resultado is not None:
            dados_ranking.append(resultado)
        progress_bar.progress((i+1)/len(tickers_validos), text=f"Simulando {ticker} ({i+1}/{len(tickers_validos)})...")
    progress_bar.empty()
    df_ranking = pd.DataFrame(dados_ranking)
    if df_ranking.empty:
        st.warning("⚠️ Não foi possível obter dados para simulação.")
        return pd.DataFrame()
    df_ranking = df_ranking.sort_values('Rentabilidade Total (%)', ascending=False)
    return df_ranking.head(13).reset_index(drop=True)

def simular_investimento_valor(ticker, data_inicio, valor_investido_inicial):
    try:
        if isinstance(data_inicio, date) and not isinstance(data_inicio, datetime):
            data_inicio = datetime(data_inicio.year, data_inicio.month, data_inicio.day)
        elif isinstance(data_inicio, str):
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
        historico = buscar_historico_precos(ticker, "max")
        if historico is None:
            return None
        precos_apos = historico[historico.index >= data_inicio]
        if precos_apos.empty:
            return None
        primeira_data = precos_apos.index[0]
        preco_compra = precos_apos['Close'].iloc[0]
        if preco_compra == 0:
            return None
        qtd_acoes = valor_investido_inicial / preco_compra
        dividendos = buscar_dividendos_historicos(ticker)
        preco_atual = historico['Close'].iloc[-1]
        total_dividendos = 0
        if dividendos is not None and not dividendos.empty:
            dividendos_apos = dividendos[dividendos['Data'] >= primeira_data]
            total_dividendos = (dividendos_apos['Dividendo'] * qtd_acoes).sum()
        valor_final_acoes = qtd_acoes * preco_atual
        ganho_total = (valor_final_acoes - valor_investido_inicial) + total_dividendos
        rentabilidade = (ganho_total / valor_investido_inicial) * 100
        dados_cotacao = buscar_cotacao_atual(ticker)
        setor = dados_cotacao.get('setor', 'N/A') if dados_cotacao else 'N/A'
        return {
            'Ticker': ticker,
            'Setor': setor,
            'Data Compra': primeira_data,
            'Valor Investido Inicial': valor_investido_inicial,
            'Valor Final Ações': valor_final_acoes,
            'Total Dividendos': total_dividendos,
            'Ganho Total': ganho_total,
            'Rentabilidade Total (%)': rentabilidade
        }
    except:
        return None

def simular_investimento_lotes(ticker, data_inicio, quantidade_acoes=100):
    try:
        if isinstance(data_inicio, date) and not isinstance(data_inicio, datetime):
            data_inicio = datetime(data_inicio.year, data_inicio.month, data_inicio.day)
        elif isinstance(data_inicio, str):
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
        historico = buscar_historico_precos(ticker, "max")
        if historico is None:
            return None
        precos_apos = historico[historico.index >= data_inicio]
        if precos_apos.empty:
            return None
        primeira_data = precos_apos.index[0]
        preco_compra = precos_apos['Close'].iloc[0]
        if preco_compra == 0:
            return {'error': True, 'message': "Preço de compra zero, simulação impossível."}
        valor_investido = quantidade_acoes * preco_compra
        preco_atual = historico['Close'].iloc[-1]
        dividendos = buscar_dividendos_historicos(ticker)
        total_dividendos = 0
        if dividendos is not None and not dividendos.empty:
            dividendos_apos = dividendos[dividendos['Data'] >= primeira_data]
            total_dividendos = (dividendos_apos['Dividendo'] * quantidade_acoes).sum()
        valor_investido_atual = quantidade_acoes * preco_atual
        ganho_preco = valor_investido_atual - valor_investido
        ganho_total = ganho_preco + total_dividendos
        rent_preco = (ganho_preco / valor_investido) * 100
        rent_div = (total_dividendos / valor_investido) * 100
        rent_total = (ganho_total / valor_investido) * 100
        return {
            'data_compra': primeira_data,
            'preco_compra': preco_compra,
            'quantidade_acoes': quantidade_acoes,
            'valor_investido': valor_investido,
            'preco_atual': preco_atual,
            'valor_investido_atual': valor_investido_atual,
            'total_dividendos_recebidos': total_dividendos,
            'ganho_preco': ganho_preco,
            'ganho_total': ganho_total,
            'rentabilidade_dividendos_percentual': rent_div,
            'rentabilidade_preco_percentual': rent_preco,
            'rentabilidade_total_percentual': rent_total,
            'sem_dividendos': total_dividendos == 0
        }
    except Exception as e:
        return {'error': True, 'message': f"Erro inesperado: {e}"}

def calcular_valuation_lucro_economico_selic(lucro_economico, selic_percentual=15):
    if lucro_economico and lucro_economico > 0:
        return lucro_economico / (selic_percentual / 100)
    return None

def criar_grafico_comparativo(preco_calculado, cotacao_atual, ticker):
    fig = go.Figure()
    max_val = max(preco_calculado, cotacao_atual) * 1.3
    min_val = min(preco_calculado, cotacao_atual) * 0.7
    preco_formatado = f"R$ {preco_calculado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    cotacao_formatada = f"R$ {cotacao_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    fig.add_trace(go.Indicator(
        mode="number+gauge+delta",
        value=cotacao_atual,
        number={'prefix': "R$ ", 'valueformat': ",.2f"},
        delta={'reference': preco_calculado, 'relative': True, 'valueformat': ".1%"},
        domain={'x': [0.1, 1], 'y': [0.1, 0.9]},
        title={'text': f"💰 {ticker} - Cotação<br><span style='font-size:0.8em'>{cotacao_formatada} vs {preco_formatado}</span>"},
        gauge={
            'shape': "bullet",
            'axis': {'range': [min_val, max_val], 'tickformat': ",.2f"},
            'threshold': {'line': {'color': "red", 'width': 2}, 'thickness': 0.75, 'value': preco_calculado},
            'steps': [
                {'range': [min_val, preco_calculado], 'color': "lightgray"},
                {'range': [preco_calculado, max_val], 'color': "lightblue"}
            ],
            'bar': {'color': "darkblue", 'thickness': 0.5}
        }
    ))
    fig.update_layout(height=200, margin=dict(l=50, r=50, t=50, b=50))
    return fig

# ==============================
# 🔧 AJUSTE: FUNÇÃO PARA BUSCAR NÚMERO DE AÇÕES NO YAHOO
# Adiciona fast_info.shares, impliedSharesOutstanding e derivação market_cap/preço.
# ==============================
@st.cache_data(ttl=3600)
def buscar_numero_acoes_yahoo(ticker):
    base = re.sub(r'\d+$', '', str(ticker)).upper()
    sufixos = ['3', '4', '5', '6', '7', '10', '11']
    total_acoes = 0
    classes_encontradas = []

    session = curl_requests.Session(impersonate="chrome")

    # Conjunto de tickers candidatos (sem duplicar)
    tickers_candidatos = []
    try:
        tk_principal = obter_ticker_yahoo(ticker)
        tickers_candidatos.append(tk_principal)
    except Exception:
        pass
    for suf in sufixos:
        t = f"{base}{suf}.SA"
        if t not in tickers_candidatos:
            tickers_candidatos.append(t)
    for extra in (f"{base}.SA", f"{str(ticker).upper()}.SA"):
        if extra not in tickers_candidatos:
            tickers_candidatos.append(extra)

    for ticker_completo in tickers_candidatos:
        try:
            acao = yf.Ticker(ticker_completo, session=session)
            shares = None

            # 1) fast_info.shares (mais confiável em 2024/2025)
            try:
                fi = acao.fast_info
                shares = getattr(fi, 'shares', None)
            except Exception:
                pass

            # 2) .info.sharesOutstanding / impliedSharesOutstanding
            if not shares:
                try:
                    info = acao.info or {}
                    shares = info.get('sharesOutstanding') or info.get('impliedSharesOutstanding')
                except Exception:
                    pass

            # 3) Derivação market_cap / last_price
            if not shares:
                try:
                    fi = acao.fast_info
                    mc = getattr(fi, 'market_cap', None)
                    px = getattr(fi, 'last_price', None)
                    if mc and px and px > 0:
                        shares = mc / px
                except Exception:
                    pass

            if shares and shares > 0:
                total_acoes += int(shares)
                classes_encontradas.append((ticker_completo, int(shares)))
        except Exception:
            pass

    return total_acoes if total_acoes > 0 else None

# ==============================
# CARREGAMENTO DOS DADOS CVM
# ==============================
@st.cache_data
def load_data():
    possible_paths = [
        "/content/capitalaberto.xlsx",
        "capitalaberto.xlsx",
        "./data/capitalaberto.xlsx",
        "/content/dff_2010_2025_final.xlsx",
        "dff_2010_2025_final.xlsx",
    ]
    data_path = None
    for path in possible_paths:
        if os.path.exists(path):
            data_path = path
            break

    if data_path is None:
        st.error(
            "❌ Arquivo de dados não encontrado.\n\n"
            "Certifique-se de que o arquivo 'capitalaberto.xlsx' está na mesma pasta do app "
            "ou em /content/ (se estiver no Colab).\n\n"
            "Caminhos verificados:\n- " + "\n- ".join(possible_paths)
        )
        st.stop()

    df = pd.read_excel(data_path)
    df.columns = [c.strip() for c in df.columns]

    if 'Pagamento de Dividendos (ou Proventos)' in df.columns:
        df.rename(columns={'Pagamento de Dividendos (ou Proventos)': 'Pagamento de Dividendos'}, inplace=True)
    if 'Patrimônio Líquido Consolidado' not in df.columns and 'Patrimônio Líquido' in df.columns:
        df.rename(columns={'Patrimônio Líquido': 'Patrimônio Líquido Consolidado'}, inplace=True)

    if 'Ticker' in df.columns:
        df['Ticker'] = df['Ticker'].fillna('').astype(str)
        df.loc[df['Ticker'] == '', 'Ticker'] = 'CD_' + df.loc[df['Ticker'] == '', 'CD_CVM'].astype(str)
    else:
        df['Ticker'] = 'CD_' + df['CD_CVM'].astype(str)

    if 'DENOM_CIA' not in df.columns:
        if 'DENOM_SOCIAL' in df.columns:
            df['DENOM_CIA'] = df['DENOM_SOCIAL']
        elif 'DENOM_COMERC' in df.columns:
            df['DENOM_CIA'] = df['DENOM_COMERC']
        else:
            df['DENOM_CIA'] = df['Ticker']
        df['DENOM_CIA'] = df['DENOM_CIA'].fillna(df['Ticker'])

    if 'SETOR_ATIV' in df.columns:
        df['is_bank'] = df['SETOR_ATIV'].str.contains('Bancos|Financeiro|Instituição Financeira', case=False, na=False)
    else:
        df['is_bank'] = False

    df = df.sort_values(['Ticker', 'Ano']).reset_index(drop=True)

    df["Ativo Médio"] = (df["Ativo Total"] + df.groupby("Ticker")["Ativo Total"].shift(1)) / 2
    df["PL Médio"] = (df["Patrimônio Líquido Consolidado"] + df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1)) / 2

    df["Passivo Oneroso Atual"] = (
        df["Empréstimos e Financiamentos - Circulante"].fillna(0) +
        df["Empréstimos e Financiamentos - Não Circulante"].fillna(0)
    )
    df["Passivo Oneroso Anterior"] = (
        df.groupby("Ticker")["Empréstimos e Financiamentos - Circulante"].shift(1).fillna(0) +
        df.groupby("Ticker")["Empréstimos e Financiamentos - Não Circulante"].shift(1).fillna(0)
    )
    df["Passivo Oneroso Médio"] = (df["Passivo Oneroso Atual"] + df["Passivo Oneroso Anterior"]) / 2

    df["Investimento Atual"] = (
        df["Empréstimos e Financiamentos - Circulante"].fillna(0) +
        df["Empréstimos e Financiamentos - Não Circulante"].fillna(0) +
        df["Patrimônio Líquido Consolidado"]
    )
    df["Investimento Anterior"] = (
        df.groupby("Ticker")["Empréstimos e Financiamentos - Circulante"].shift(1).fillna(0) +
        df.groupby("Ticker")["Empréstimos e Financiamentos - Não Circulante"].shift(1).fillna(0) +
        df.groupby("Ticker")["Patrimônio Líquido Consolidado"].shift(1).fillna(0)
    )
    df["Investimento Médio"] = (df["Investimento Atual"] + df["Investimento Anterior"]) / 2

    df["ROA"] = np.where(
        df["Ativo Médio"] > 0,
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Ativo Médio"],
        np.nan
    )
    df["ROE"] = np.where(
        df["PL Médio"] > 0,
        df["Lucro/Prejuízo Consolidado do Período"] / df["PL Médio"],
        np.nan
    )
    df["ROI"] = np.where(
        (df["Investimento Médio"] > 0) & (~df['is_bank']),
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Investimento Médio"],
        np.nan
    )

    df["Margem Bruta"] = np.where(
        df["Receita de Venda de Bens e/ou Serviços"] > 0,
        df["Resultado Bruto"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )
    df["Margem Operacional"] = np.where(
        df["Receita de Venda de Bens e/ou Serviços"] > 0,
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )
    df["Margem Líquida"] = np.where(
        (df["Receita de Venda de Bens e/ou Serviços"] > 0) & (~df['is_bank']),
        df["Lucro/Prejuízo Consolidado do Período"] / df["Receita de Venda de Bens e/ou Serviços"],
        np.nan
    )

    df["Total Passivo"] = (
        df["Passivo Circulante"].fillna(0) +
        df["Passivo Não Circulante"].fillna(0) +
        df["Patrimônio Líquido Consolidado"].fillna(0)
    )
    df["Percentual Capital Terceiros"] = np.where(
        (df["Total Passivo"] > 0) & (~df['is_bank']),
        (df["Passivo Circulante"].fillna(0) + df["Passivo Não Circulante"].fillna(0)) / df["Total Passivo"],
        np.nan
    )
    df["Percentual Capital Próprio"] = np.where(
        (df["Total Passivo"] > 0) & (~df['is_bank']),
        df["Patrimônio Líquido Consolidado"] / df["Total Passivo"],
        np.nan
    )

    df["ki"] = np.where(
        (~df['is_bank']) & (df["Passivo Oneroso Médio"] > 0) & (df["Despesas Financeiras"].notna()),
        df["Despesas Financeiras"].abs() / df["Passivo Oneroso Médio"],
        np.nan
    )
    df["ke"] = np.where(
        (~df['is_bank']) & (df["PL Médio"] > 0) & (df["Pagamento de Dividendos"].notna()),
        df["Pagamento de Dividendos"].abs() / df["PL Médio"],
        np.nan
    )
    df["wacc"] = np.where(
        (~df['is_bank']) &
        (df["ki"].notna()) & (df["ke"].notna()) &
        (df["Percentual Capital Terceiros"].notna()) & (df["Percentual Capital Próprio"].notna()),
        (df["ki"] * df["Percentual Capital Terceiros"]) + (df["ke"] * df["Percentual Capital Próprio"]),
        np.nan
    )

    if 'Depreciação e Amortização' in df.columns:
        depreciacao_amortizacao = abs(df['Depreciação e Amortização'].fillna(0))
        df["EBITDA"] = np.where(
            ~df['is_bank'] & df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna(),
            df["Resultado Antes do Resultado Financeiro e dos Tributos"] + depreciacao_amortizacao,
            np.nan
        )
    else:
        df["EBITDA"] = np.where(~df['is_bank'], df["Resultado Antes do Resultado Financeiro e dos Tributos"], np.nan)

    df["Lucro Econômico 1"] = np.where(
        (~df['is_bank']) &
        (df["ROI"].notna()) & (df["wacc"].notna()) & (df["Investimento Médio"].notna()),
        (df["ROI"] - df["wacc"]) * df["Investimento Médio"],
        np.nan
    )
    df["Lucro Econômico 2"] = np.where(
        (~df['is_bank']) &
        (df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna()) &
        (df["wacc"].notna()) &
        (df["Investimento Médio"].notna()),
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] - (df["wacc"] * df["Investimento Médio"]),
        np.nan
    )
    df["Diferença Lucro Econômico"] = abs(df["Lucro Econômico 1"] - df["Lucro Econômico 2"])

    df["Alavancagem Eficaz"] = np.where(
        (~df['is_bank']) &
        (df["ROE"].notna()) & (df["ROA"].notna()) & (df["ROI"].notna()),
        (df["ROE"] > df["ROA"]) & (df["ROE"] > df["ROI"]),
        False
    )

    return df
