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
from datetime import datetime, timedelta, date
import locale
import time

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
        return "N/A"
    try:
        return f"{valor:.{casas_decimais}%}".replace(".", ",")
    except:
        return str(valor)

def formatar_dataframe_percentual(df, colunas):
    df_formatado = df.copy()
    for coluna in colunas:
        if coluna in df_formatado.columns:
            df_formatado[coluna] = df_formatado[coluna].apply(
                lambda x: formatar_percentual_brasil(x, 2) if pd.notna(x) else "N/A"
            )
    return df_formatado

# ==============================
# FUNÇÕES DE MERCADO E DIVIDENDOS (com cache)
# ==============================
@st.cache_data(ttl=86400)
def buscar_cotacao_atual(ticker):
    try:
        ticker_yf = f"{ticker}.SA"
        acao = yf.Ticker(ticker_yf)
        info = acao.info
        cotacao = info.get('regularMarketPrice') or info.get('currentPrice')
        if cotacao and cotacao > 0:
            return {
                'cotacao': cotacao,
                'moeda': info.get('currency', 'BRL'),
                'nome': info.get('longName', ticker),
                'setor': info.get('sector', 'N/A'),
                'industria': info.get('industry', 'N/A'),
                'market_cap': info.get('marketCap'),
                'sharesOutstanding': info.get('sharesOutstanding'),
                'volume': info.get('volume'),
                'data_atualizacao': datetime.now().strftime("%d/%m/%Y %H:%M")
            }
    except:
        pass
    return None

@st.cache_data(ttl=86400)
def buscar_dividendos_historicos(ticker):
    try:
        ticker_yf = f"{ticker}.SA"
        acao = yf.Ticker(ticker_yf)
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

@st.cache_data(ttl=86400)
def buscar_historico_precos(ticker, periodo_maximo="max"):
    try:
        ticker_yf = f"{ticker}.SA"
        acao = yf.Ticker(ticker_yf)
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
    """
    Usa os dados da DFC (coluna 'Pagamento de Dividendos') para identificar
    tickers que pagaram dividendos/JCP em pelo menos 'minimo_anos_com_pagamento'
    dos últimos 'anos_verificar' anos disponíveis no dataset.
    """
    st.info(f"🔎 **Pré‑filtro:** Buscando tickers com pagamento de dividendos em pelo menos {minimo_anos_com_pagamento} dos últimos {anos_verificar} anos.")
    
    # Pegar os últimos N anos disponíveis no dataset
    anos_disponiveis = sorted(df_cvm['Ano'].unique(), reverse=True)
    ultimos_anos = anos_disponiveis[:anos_verificar]
    
    # Lista de tickers únicos
    tickers_validos = df_cvm['Ticker'].unique()
    tickers_consistentes = []
    
    progress_bar = st.progress(0, text="Verificando consistência de dividendos...")
    for i, ticker in enumerate(tickers_validos):
        # Filtrar dados do ticker para os últimos anos
        df_ticker = df_cvm[(df_cvm['Ticker'] == ticker) & (df_cvm['Ano'].isin(ultimos_anos))]
        
        # Verificar se há dados de pagamento de dividendos
        if 'Pagamento de Dividendos' not in df_ticker.columns:
            continue
        
        # Contar anos com pagamento > 0
        pagamentos = df_ticker[df_ticker['Pagamento de Dividendos'].notna() & (df_ticker['Pagamento de Dividendos'] != 0)]
        anos_com_pagamento = pagamentos['Ano'].nunique()
        
        if anos_com_pagamento >= minimo_anos_com_pagamento:
            tickers_consistentes.append(ticker)
        
        # Progresso
        progress_bar.progress((i+1)/len(tickers_validos), text=f"Verificando {ticker} ({i+1}/{len(tickers_validos)})...")
    
    progress_bar.empty()
    st.success(f"✅ {len(tickers_consistentes)} tickers com pagamento consistente (≥ {minimo_anos_com_pagamento} anos nos últimos {anos_verificar}).")
    return tickers_consistentes

def calcular_ranking_dividendos(tickers_consistentes, df_cvm, periodo_dy_anos=10):
    """
    Calcula o DY médio para os tickers consistentes.
    O setor é extraído do próprio dataset (SETOR_ATIV), não do Yahoo.
    """
    dados_ranking = []
    if not tickers_consistentes:
        return pd.DataFrame()
    
    # Criar mapa de setores a partir do dataset (pegar o setor mais recente disponível)
    # Pegar o ano mais recente no dataset
    ano_recente = df_cvm['Ano'].max()
    setor_map = df_cvm[df_cvm['Ano'] == ano_recente][['Ticker', 'SETOR_ATIV']].drop_duplicates(subset=['Ticker'])
    setor_map = setor_map.set_index('Ticker')['SETOR_ATIV'].to_dict()
    
    st.warning(f"⚠️ Calculando DY médio de {periodo_dy_anos} anos para {len(tickers_consistentes)} tickers.")
    progress_bar = st.progress(0, text="Buscando dados de mercado...")
    
    for i, ticker in enumerate(tickers_consistentes):
        dados_cotacao = buscar_cotacao_atual(ticker)
        data_inicio = datetime.now() - timedelta(days=365 * periodo_dy_anos)
        df_precos = buscar_historico_precos(ticker, "max")
        df_div = buscar_dividendos_historicos(ticker)
        dy_medio = None
        
        if dados_cotacao and df_precos is not None and df_div is not None and not df_div.empty:
            df_precos_filt = df_precos[df_precos.index >= data_inicio]
            df_div_filt = df_div[df_div['Data'] >= data_inicio]
            if not df_precos_filt.empty and not df_div_filt.empty:
                try:
                    # CORREÇÃO: usar 'YE' em vez de 'Y' (depreciado)
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
            # Usar SETOR_ATIV do dataset (em português), fallback para o Yahoo se não encontrar
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

    # Normalização
    if 'Pagamento de Dividendos (ou Proventos)' in df.columns:
        df.rename(columns={'Pagamento de Dividendos (ou Proventos)': 'Pagamento de Dividendos'}, inplace=True)
    if 'Patrimônio Líquido Consolidado' not in df.columns and 'Patrimônio Líquido' in df.columns:
        df.rename(columns={'Patrimônio Líquido': 'Patrimônio Líquido Consolidado'}, inplace=True)

    # Garantir que Ticker esteja preenchido (fallback para CD_CVM)
    if 'Ticker' in df.columns:
        df['Ticker'] = df['Ticker'].fillna('').astype(str)
        df.loc[df['Ticker'] == '', 'Ticker'] = 'CD_' + df.loc[df['Ticker'] == '', 'CD_CVM'].astype(str)
    else:
        df['Ticker'] = 'CD_' + df['CD_CVM'].astype(str)

    # Garantir que DENOM_CIA exista
    if 'DENOM_CIA' not in df.columns:
        if 'DENOM_SOCIAL' in df.columns:
            df['DENOM_CIA'] = df['DENOM_SOCIAL']
        elif 'DENOM_COMERC' in df.columns:
            df['DENOM_CIA'] = df['DENOM_COMERC']
        else:
            df['DENOM_CIA'] = df['Ticker']
        df['DENOM_CIA'] = df['DENOM_CIA'].fillna(df['Ticker'])

    # Identificar bancos
    if 'SETOR_ATIV' in df.columns:
        df['is_bank'] = df['SETOR_ATIV'].str.contains('Bancos|Financeiro|Instituição Financeira', case=False, na=False)
    else:
        df['is_bank'] = False

    df = df.sort_values(['Ticker', 'Ano']).reset_index(drop=True)

    # Cálculo de médias e indicadores
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

# ==============================
# CONFIGURAÇÃO DO STREAMLIT
# ==============================
st.set_page_config(page_title="Dashboard Capital Aberto", layout="wide")
st.title("📊 Dashboard Capital Aberto")

# Carregar dados
df = load_data()

# ==============================
# SIDEBAR – FILTROS
# ==============================
st.sidebar.header("🔧 Filtros")

executar_pre_filtro = st.sidebar.checkbox(
    "Pré‑filtro de dividendos consistentes",
    value=False,
    help="Busca tickers que pagaram dividendos anualmente desde 2010"
)

modo_analise = st.sidebar.radio(
    "Modo de Análise",
    ["🏆 Dados Gerais", "📈 Visão por Empresa", "🏭 Análise Setorial"]
)

anos_disponiveis = sorted(df["Ano"].unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Ano:", anos_disponiveis)

# Lista de tickers para o seletor (apenas ticker)
tickers_disponiveis = sorted(df["Ticker"].dropna().unique())

if modo_analise == "📈 Visão por Empresa":
    ticker_selecionado = st.sidebar.selectbox("Empresa:", tickers_disponiveis)
    df_filtrado = df[(df["Ticker"] == ticker_selecionado) & (df["Ano"] == ano_selecionado)]
    df_empresa_todos_anos = df[df["Ticker"] == ticker_selecionado].sort_values("Ano")
elif modo_analise == "🏭 Análise Setorial":
    setor_selecionado = st.sidebar.selectbox("Setor:", sorted(df["SETOR_ATIV"].dropna().unique()))
    df_filtrado = df[(df["SETOR_ATIV"] == setor_selecionado) & (df["Ano"] == ano_selecionado)]
    df_setor_todos_anos = df[df["SETOR_ATIV"] == setor_selecionado].sort_values(["Ano", "Ticker"])
else:  # Dados Gerais
    df_filtrado = df[df["Ano"] == ano_selecionado]

# Variável global para tickers consistentes (será preenchida se ativado)
TICKERS_CONSISTENTES = []
if executar_pre_filtro:
    TICKERS_CONSISTENTES = calcular_tickers_consistentes(df)

# ==============================
# MODO: DADOS GERAIS
# ==============================
if modo_analise == "🏆 Dados Gerais":
    st.header(f"🏆 Ano: {ano_selecionado}")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Empresas", df_filtrado["Ticker"].nunique())
    with col2:
        st.metric("Setores", df_filtrado["SETOR_ATIV"].nunique())
    with col3:
        receita_total = df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum()
        st.metric("Receita Total", formatar_moeda_brasil_correta(receita_total, 2))
    with col4:
        lucro_total = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum()
        st.metric("Lucro Total", formatar_moeda_brasil_correta(lucro_total, 2))
    st.divider()

    tabs = st.tabs(["📈 Rentabilidade", "💰 Lucro/Receita/Caixa", "🏛️ Solidez", "📊 Eficiência", "👑 Dividendos Consistentes", "🚀 Maior Retorno"])

    # --- Aba 1: Rentabilidade ---
    with tabs[0]:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 15 ROE")
            roe = df_filtrado[df_filtrado["ROE"].notna()].nlargest(15, "ROE")[["Ticker", "SETOR_ATIV", "ROE"]]
            if not roe.empty:
                fig = px.bar(roe, x="Ticker", y="ROE", color="SETOR_ATIV", title="ROE")
                fig.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.subheader("Top 15 ROA")
            roa = df_filtrado[df_filtrado["ROA"].notna()].nlargest(15, "ROA")[["Ticker", "SETOR_ATIV", "ROA"]]
            if not roa.empty:
                fig = px.bar(roa, x="Ticker", y="ROA", color="SETOR_ATIV", title="ROA")
                fig.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig, use_container_width=True)
        st.subheader("📋 Top 20 Rentabilidade")
        rent = df_filtrado[df_filtrado["ROE"].notna() & df_filtrado["ROA"].notna()].nlargest(20, "ROE")[["Ticker", "SETOR_ATIV", "ROE", "ROA", "ROI", "Margem Líquida"]]
        if not rent.empty:
            st.dataframe(formatar_dataframe_percentual(rent, ['ROE', 'ROA', 'ROI', 'Margem Líquida']), use_container_width=True)

    # --- Aba 2: Lucro/Receita/Caixa ---
    with tabs[1]:
        st.subheader("🥇 Top 13 Caixa Operacional")
        fco = "Caixa Líquido Atividades Operacionais"
        fco_rank = df_filtrado[df_filtrado[fco].notna()].nlargest(13, fco)[["Ticker", "SETOR_ATIV", fco]]
        if not fco_rank.empty:
            fco_rank["Caixa Op (R$)"] = fco_rank[fco] * 1000 / 1e9
            fig = px.bar(fco_rank, x="Ticker", y="Caixa Op (R$)", color="SETOR_ATIV", title="Caixa Operacional (R$ Bi)")
            fig.update_layout(yaxis_tickformat=',.2f')
            st.plotly_chart(fig, use_container_width=True)
            fco_rank["Caixa Operacional"] = fco_rank[fco].apply(formatar_moeda_brasil_correta)
            st.dataframe(fco_rank[["Ticker", "SETOR_ATIV", "Caixa Operacional"]], use_container_width=True)
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 15 Lucro Líquido")
            lucro = df_filtrado.nlargest(15, "Lucro/Prejuízo Consolidado do Período")[["Ticker", "SETOR_ATIV", "Lucro/Prejuízo Consolidado do Período"]]
            if not lucro.empty:
                lucro["Lucro (R$)"] = lucro["Lucro/Prejuízo Consolidado do Período"] * 1000 / 1e9
                fig = px.bar(lucro, x="Ticker", y="Lucro (R$)", color="SETOR_ATIV", title="Lucro Líquido (R$ Bi)")
                fig.update_layout(yaxis_tickformat=',.2f')
                st.plotly_chart(fig, use_container_width=True)
                lucro["Lucro"] = lucro["Lucro/Prejuízo Consolidado do Período"].apply(formatar_moeda_brasil_correta)
                st.dataframe(lucro[["Ticker", "SETOR_ATIV", "Lucro"]], use_container_width=True)
        with col2:
            st.subheader("Top 15 Receita")
            rec = df_filtrado.nlargest(15, "Receita de Venda de Bens e/ou Serviços")[["Ticker", "SETOR_ATIV", "Receita de Venda de Bens e/ou Serviços"]]
            if not rec.empty:
                rec["Receita (R$)"] = rec["Receita de Venda de Bens e/ou Serviços"] * 1000 / 1e9
                fig = px.bar(rec, x="Ticker", y="Receita (R$)", color="SETOR_ATIV", title="Receita (R$ Bi)")
                fig.update_layout(yaxis_tickformat=',.2f')
                st.plotly_chart(fig, use_container_width=True)
                rec["Receita"] = rec["Receita de Venda de Bens e/ou Serviços"].apply(formatar_moeda_brasil_correta)
                st.dataframe(rec[["Ticker", "SETOR_ATIV", "Receita"]], use_container_width=True)

    # --- Aba 3: Solidez ---
    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 15 Patrimônio Líquido")
            pl = df_filtrado.nlargest(15, "Patrimônio Líquido Consolidado")[["Ticker", "SETOR_ATIV", "Patrimônio Líquido Consolidado"]]
            if not pl.empty:
                pl["PL (R$)"] = pl["Patrimônio Líquido Consolidado"] * 1000 / 1e9
                fig = px.bar(pl, x="Ticker", y="PL (R$)", color="SETOR_ATIV", title="PL (R$ Bi)")
                fig.update_layout(yaxis_tickformat=',.2f')
                st.plotly_chart(fig, use_container_width=True)
                pl["PL"] = pl["Patrimônio Líquido Consolidado"].apply(formatar_moeda_brasil_correta)
                st.dataframe(pl[["Ticker", "SETOR_ATIV", "PL"]], use_container_width=True)
        with col2:
            st.subheader("Top 15 ROI")
            roi = df_filtrado[df_filtrado["ROI"].notna()].nlargest(15, "ROI")[["Ticker", "SETOR_ATIV", "ROI"]]
            if not roi.empty:
                fig = px.bar(roi, x="Ticker", y="ROI", color="SETOR_ATIV", title="ROI")
                fig.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig, use_container_width=True)

    # --- Aba 4: Eficiência ---
    with tabs[3]:
        st.subheader("Top 15 Margem Líquida")
        margem = df_filtrado[df_filtrado["Margem Líquida"].notna()].nlargest(15, "Margem Líquida")[["Ticker", "SETOR_ATIV", "Margem Líquida"]]
        if not margem.empty:
            fig = px.bar(margem, x="Ticker", y="Margem Líquida", color="SETOR_ATIV", title="Margem Líquida")
            fig.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(formatar_dataframe_percentual(margem, ['Margem Líquida']), use_container_width=True)
        st.subheader("Melhor WACC")
        wacc = df_filtrado[df_filtrado["wacc"].notna()].nsmallest(15, "wacc")[["Ticker", "SETOR_ATIV", "wacc"]]
        if not wacc.empty:
            fig = px.bar(wacc, x="Ticker", y="wacc", color="SETOR_ATIV", title="WACC (menor é melhor)")
            fig.update_layout(yaxis_tickformat=',.2%')
            st.plotly_chart(fig, use_container_width=True)

    # --- Aba 5: Dividendos Consistentes (CORRIGIDA) ---
    with tabs[4]:
        st.subheader("👑 Top 10 - Dividend Yield Médio (Empresas Consistentes)")
        if executar_pre_filtro:
            with st.spinner("🔍 Buscando tickers com dividendos consistentes..."):
                if not TICKERS_CONSISTENTES:
                    TICKERS_CONSISTENTES = calcular_tickers_consistentes(df)
            if TICKERS_CONSISTENTES:
                df_dy = calcular_ranking_dividendos(TICKERS_CONSISTENTES, df, periodo_dy_anos=10)
                if not df_dy.empty:
                    top10 = df_dy[df_dy['DY Médio (10A)'].notna()].nlargest(10, 'DY Médio (10A)').reset_index(drop=True)
                    if not top10.empty:
                        top10.index = top10.index + 1
                        top10 = top10.rename(columns={'DY Médio (10A)': 'DY Médio (10 Anos)'})
                        display = top10.copy()
                        display['DY Médio (10 Anos)'] = display['DY Médio (10 Anos)'].apply(lambda x: formatar_percentual_brasil(x/100, 2) if pd.notna(x) else 'N/A')
                        display['Cotação Atual'] = display['Cotação Atual'].apply(lambda x: f"R$ {formatar_numero_brasil_correto(x, 2)}")
                        st.dataframe(display, use_container_width=True)
                        fig = px.bar(top10, x="Ticker", y="DY Médio (10 Anos)", color="Setor", title="DY Médio dos Últimos 10 Anos")
                        fig.update_layout(yaxis_tickformat='.2f')
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Nenhum ticker consistente com DY calculado.")
                else:
                    st.warning("Não foi possível calcular o DY médio para os tickers consistentes.")
            else:
                st.info("Nenhum ticker com pagamento de dividendos anuais consistentes desde 2010.")
        else:
            st.info("Pré‑filtro de dividendos consistentes desativado. Ative na barra lateral.")

    # --- Aba 6: Maior Retorno ---
    with tabs[5]:
        st.header("🚀 Top 13 - Maior Retorno Total (Valorização + Dividendos)")
        st.markdown("Simulação de investimento fixo, considerando proventos recebidos.")
        col_data, col_valor = st.columns(2)
        with col_data:
            data_hoje = date.today()
            data_inicio = st.date_input(
                "Data de início:",
                value=data_hoje - timedelta(days=365*5),
                min_value=datetime(2010,1,1).date(),
                max_value=data_hoje - timedelta(days=1)
            )
        with col_valor:
            valores = [1000, 10000, 100000, 1000000, 10000000]
            valor_investido = st.selectbox(
                "Valor investido:",
                options=valores,
                index=2,
                format_func=lambda x: f"R$ {formatar_numero_brasil_correto(x, 0)}"
            )
        if st.button(f"✨ Calcular TOP 13"):
            data_para_sim = datetime.combine(data_inicio, datetime.min.time())
            todos_tickers = df["Ticker"].dropna().unique()
            df_ret = calcular_ranking_retorno_total(list(todos_tickers), data_para_sim, valor_investido)
            if not df_ret.empty:
                st.subheader(f"🥇 TOP 13 em Retorno Total (Investimento em {data_para_sim.strftime('%d/%m/%Y')})")
                display = df_ret.copy()
                display.index = display.index + 1
                display = display.rename(columns={
                    'Rentabilidade Total (%)': 'Retorno Total (%)',
                    'Valor Investido Inicial': 'Investido (R$)',
                    'Valor Final Ações': 'Valor Atual (R$)',
                    'Total Dividendos': 'Proventos (R$)',
                    'Ganho Total': 'Ganho Total (R$)'
                })
                display = display[['Ticker', 'Setor', 'Retorno Total (%)', 'Investido (R$)', 'Valor Atual (R$)', 'Proventos (R$)', 'Ganho Total (R$)']]
                display['Retorno Total (%)'] = display['Retorno Total (%)'].apply(lambda x: formatar_percentual_brasil(x/100, 2) if pd.notna(x) else 'N/A')
                display['Investido (R$)'] = display['Investido (R$)'].apply(lambda x: formatar_numero_brasil_correto(x, 0))
                display['Valor Atual (R$)'] = display['Valor Atual (R$)'].apply(lambda x: formatar_numero_brasil_correto(x, 2))
                display['Proventos (R$)'] = display['Proventos (R$)'].apply(lambda x: formatar_numero_brasil_correto(x, 2))
                display['Ganho Total (R$)'] = display['Ganho Total (R$)'].apply(lambda x: formatar_numero_brasil_correto(x, 2))
                st.dataframe(display, use_container_width=True)
                fig = px.bar(df_ret.head(13), x='Ticker', y='Rentabilidade Total (%)', color='Setor',
                             title=f"Retorno Total (Investido R$ {formatar_numero_brasil_correto(valor_investido, 0)})")
                fig.update_layout(yaxis_tickformat='.2f')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Não foi possível calcular o retorno para nenhum ticker com a data selecionada.")

# ==============================
# MODO: VISÃO POR EMPRESA
# ==============================
elif modo_analise == "📈 Visão por Empresa":
    st.header(f"📊 Análise Detalhada - {ticker_selecionado}")
    if not df_empresa_todos_anos.empty:
        dados_cotacao = buscar_cotacao_atual(ticker_selecionado)
        col1, col2, col3 = st.columns([1,1,2])
        with col1:
            st.metric("Ano Fiscal", ano_selecionado)
        with col2:
            st.metric("Setor", df_filtrado["SETOR_ATIV"].iloc[0] if not df_filtrado.empty else "N/A")
        with col3:
            if dados_cotacao:
                st.metric("Cotação Atual", f"R$ {dados_cotacao['cotacao']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                         delta=f"Atualizado: {dados_cotacao['data_atualizacao']}")
            else:
                st.metric("Cotação", "N/A")
        st.divider()

        tab_atual, tab_evolucao, tab_dividendos, tab_simulacao = st.tabs(["📊 Análise do Ano", "📈 Evolução Temporal", "💰 Dividendos", "💵 Simulação Investimento"])

        # --- Aba Análise do Ano ---
        with tab_atual:
            st.subheader(f"Ano {ano_selecionado}")
            if not df_filtrado.empty:
                is_bank = df_filtrado['is_bank'].iloc[0] if 'is_bank' in df_filtrado.columns else False
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("ROE", formatar_percentual_brasil(df_filtrado["ROE"].iloc[0], 2) if pd.notna(df_filtrado["ROE"].iloc[0]) else "-")
                with col2:
                    st.metric("ROA", formatar_percentual_brasil(df_filtrado["ROA"].iloc[0], 2) if pd.notna(df_filtrado["ROA"].iloc[0]) else "-")
                with col3:
                    if not is_bank:
                        st.metric("ROI", formatar_percentual_brasil(df_filtrado["ROI"].iloc[0], 2) if pd.notna(df_filtrado["ROI"].iloc[0]) else "-")
                    else:
                        st.metric("ROI", "N/A (Banco)")
                with col4:
                    if not is_bank:
                        st.metric("WACC", formatar_percentual_brasil(df_filtrado["wacc"].iloc[0], 2) if pd.notna(df_filtrado["wacc"].iloc[0]) else "-")
                    else:
                        st.metric("WACC", "N/A (Banco)")
                with col5:
                    if 'Caixa Líquido Atividades Operacionais' in df_filtrado.columns:
                        val = df_filtrado['Caixa Líquido Atividades Operacionais'].iloc[0]
                        st.metric("Caixa Operacional", formatar_moeda_brasil_correta(val) if pd.notna(val) else "N/A")
                    else:
                        st.metric("Caixa Operacional*", "N/A")

                if not is_bank:
                    st.subheader("🔍 Verificação: Lucro Econômico 1 vs 2")
                    le1 = df_filtrado["Lucro Econômico 1"].iloc[0]
                    le2 = df_filtrado["Lucro Econômico 2"].iloc[0]
                    if pd.notna(le1) and pd.notna(le2):
                        diff = abs(le1 - le2)
                        tol = max(abs(le1), abs(le2)) * 0.001
                        if diff <= tol:
                            st.success("✅ Lucro Econômico 1 = Lucro Econômico 2")
                            st.write(f"LE1: {formatar_moeda_brasil_correta(le1)}")
                            st.write(f"LE2: {formatar_moeda_brasil_correta(le2)}")
                        else:
                            st.error("❌ LE1 ≠ LE2")
                            st.write(f"LE1: {formatar_moeda_brasil_correta(le1)}")
                            st.write(f"LE2: {formatar_moeda_brasil_correta(le2)}")
                    else:
                        st.info("Dados de Lucro Econômico não disponíveis.")
                    st.subheader("🔍 Análise de Alavancagem")
                    if pd.notna(df_filtrado["Alavancagem Eficaz"].iloc[0]):
                        if df_filtrado["Alavancagem Eficaz"].iloc[0]:
                            st.success("✅ Alavancagem com Eficácia: SIM")
                            st.write(f"ROE ({formatar_percentual_brasil(df_filtrado['ROE'].iloc[0], 2)}) > ROA ({formatar_percentual_brasil(df_filtrado['ROA'].iloc[0], 2)})")
                        else:
                            st.warning("⚠️ Alavancagem com Eficácia: NÃO")
                st.divider()

                sub_tabs = st.tabs(["📈 Rentabilidade", "🏦 Valuation", "🏛️ Estrutura", "💸 Custo", "📊 Lucro Econômico", "💵 Fluxo de Caixa", "📋 Dados Brutos"])
                with sub_tabs[0]:
                    st.subheader("Rentabilidade")
                    cols = ["ROE", "ROA", "ROI", "Margem Bruta", "Margem Operacional", "Margem Líquida"] if not is_bank else ["ROE", "ROA", "Margem Bruta", "Margem Operacional"]
                    data = []
                    for c in cols:
                        if c in df_filtrado.columns:
                            val = df_filtrado[c].iloc[0]
                            data.append({"Indicador": c, "Valor": formatar_percentual_brasil(val, 2) if pd.notna(val) else "N/A"})
                    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

                with sub_tabs[1]:
                    if is_bank:
                        st.subheader("🏦 Valuation para Bancos")
                        ra = df_filtrado['Resultado Abrangente do Período'].iloc[0] if 'Resultado Abrangente do Período' in df_filtrado.columns else None
                        pl_medio = df_filtrado['PL Médio'].iloc[0] if 'PL Médio' in df_filtrado.columns else None
                        num_acoes = df_filtrado['Numero_Acoes'].iloc[0] if 'Numero_Acoes' in df_filtrado.columns and pd.notna(df_filtrado['Numero_Acoes'].iloc[0]) else None
                        if not num_acoes and dados_cotacao and dados_cotacao.get('sharesOutstanding'):
                            num_acoes = dados_cotacao['sharesOutstanding']
                        if ra and pl_medio and num_acoes and num_acoes > 0:
                            col_selic1, col_selic2 = st.columns([2,1])
                            with col_selic2:
                                selic = st.number_input("SELIC (%)", min_value=0.1, max_value=30.0, value=13.5, step=0.1)
                            lpa = ra / num_acoes
                            vpa = pl_medio / num_acoes
                            r = selic / 100
                            cotacao_esp = (lpa - (vpa * r)) / r
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Resultado Abrangente", formatar_moeda_brasil_correta(ra))
                            col2.metric("PL Médio", formatar_moeda_brasil_correta(pl_medio))
                            col3.metric("Nº de Ações", formatar_numero_brasil_correto(num_acoes, 0))
                            col4.metric("Cotação Esperada", f"R$ {cotacao_esp:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                            st.info(f"""
                            **Fórmula:** LPA = {formatar_moeda_brasil_correta(ra)} / {formatar_numero_brasil_correto(num_acoes, 0)} = R$ {lpa:,.2f}
                            VPA = {formatar_moeda_brasil_correta(pl_medio)} / {formatar_numero_brasil_correto(num_acoes, 0)} = R$ {vpa:,.2f}
                            Cotação = (LPA - VPA × r) / r = ({lpa:,.2f} - {vpa:,.2f} × {r:.3f}) / {r:.3f} = R$ {cotacao_esp:,.2f}
                            """)
                            if dados_cotacao:
                                st.subheader("Comparação com Mercado")
                                col1, col2 = st.columns(2)
                                col1.metric("Cotação Atual", f"R$ {dados_cotacao['cotacao']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                diff_pct = ((dados_cotacao['cotacao'] - cotacao_esp) / cotacao_esp) * 100
                                col2.metric("Diferença", f"{diff_pct:+.1f}%")
                                if diff_pct > 20:
                                    st.error("🔴 Sobrevalorizado")
                                elif diff_pct < -20:
                                    st.success("🟢 Subvalorizado")
                                else:
                                    st.info("🟡 Valuation próximo")
                        else:
                            st.warning("Dados insuficientes para valuation de bancos.")
                    else:
                        st.subheader("📊 EBITDA")
                        ebitda = df_filtrado["EBITDA"].iloc[0] if "EBITDA" in df_filtrado.columns and pd.notna(df_filtrado["EBITDA"].iloc[0]) else None
                        op = df_filtrado["Resultado Antes do Resultado Financeiro e dos Tributos"].iloc[0] if pd.notna(df_filtrado["Resultado Antes do Resultado Financeiro e dos Tributos"].iloc[0]) else None
                        if ebitda and op:
                            col1, col2 = st.columns(2)
                            col1.metric("EBITDA", formatar_moeda_brasil_correta(ebitda))
                            col2.metric("Resultado Operacional", formatar_moeda_brasil_correta(op))
                            if 'Depreciação e Amortização' in df_filtrado.columns and pd.notna(df_filtrado['Depreciação e Amortização'].iloc[0]):
                                dep = df_filtrado['Depreciação e Amortização'].iloc[0]
                                st.write(f"**Depreciação e Amortização:** {formatar_moeda_brasil_correta(abs(dep))}")
                                st.write(f"**EBITDA = {formatar_moeda_brasil_correta(op)} + {formatar_moeda_brasil_correta(abs(dep))} = {formatar_moeda_brasil_correta(ebitda)}**")
                            st.divider()
                            st.subheader("🏦 Valuation por Lucro Econômico/SELIC")
                            col_selic1, col_selic2 = st.columns([2,1])
                            with col_selic2:
                                selic = st.number_input("SELIC (%)", min_value=0.1, max_value=30.0, value=15.0, step=0.1)
                            le = df_filtrado["Lucro Econômico 1"].iloc[0] if "Lucro Econômico 1" in df_filtrado.columns and pd.notna(df_filtrado["Lucro Econômico 1"].iloc[0]) else None
                            if le and le > 0:
                                val_emp = calcular_valuation_lucro_economico_selic(le, selic)
                                if val_emp:
                                    val_emp_reais = val_emp * 1000
                                    num_acoes = df_filtrado['Numero_Acoes'].iloc[0] if 'Numero_Acoes' in df_filtrado.columns and pd.notna(df_filtrado['Numero_Acoes'].iloc[0]) else None
                                    cotacao_esp = val_emp_reais / num_acoes if num_acoes and num_acoes > 0 else None
                                    col1, col2, col3, col4 = st.columns(4)
                                    col1.metric("Valor da Empresa (EV)", formatar_moeda_brasil_correta(val_emp_reais / 1000))
                                    col2.metric("Valor da Empresa", formatar_moeda_brasil_correta(val_emp_reais / 1000))
                                    col3.metric("Nº de Ações", formatar_numero_brasil_correto(num_acoes, 0) if num_acoes else "N/A")
                                    col4.metric("Cotação Esperada", f"R$ {cotacao_esp:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if cotacao_esp else "N/A")
                                    st.info(f"""
                                    **Fórmula:** Valor da Empresa = Lucro Econômico ÷ (SELIC/100)
                                    = {formatar_moeda_brasil_correta(le)} / ({selic}%/100) = {formatar_moeda_brasil_correta(val_emp)}
                                    Valor (R$) = {formatar_moeda_brasil_correta(val_emp)} × 1.000 = {formatar_moeda_brasil_correta(val_emp_reais / 1000)}
                                    """)
                                    if dados_cotacao and cotacao_esp:
                                        st.divider()
                                        st.subheader("Comparação com Mercado")
                                        col1, col2, col3, col4 = st.columns(4)
                                        col1.metric("Cotação Atual", f"R$ {dados_cotacao['cotacao']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                        diff_pct = ((dados_cotacao['cotacao'] - cotacao_esp) / cotacao_esp) * 100
                                        col2.metric("Diferença", f"{diff_pct:+.1f}%")
                                        col3.metric("Setor", dados_cotacao['setor'])
                                        if dados_cotacao['market_cap']:
                                            col4.metric("Market Cap", f"R$ {dados_cotacao['market_cap']/1e12:,.2f} tri".replace(",", "X").replace(".", ",").replace("X", "."))
                                        if diff_pct > 20:
                                            st.error("🔴 Sobrevalorizado")
                                        elif diff_pct < -20:
                                            st.success("🟢 Subvalorizado")
                                        else:
                                            st.info("🟡 Valuation próximo")
                            else:
                                st.warning("Dados de Lucro Econômico não disponíveis.")
                        else:
                            st.warning("Dados de EBITDA não disponíveis.")

                with sub_tabs[2]:
                    if is_bank:
                        st.info("ℹ️ Análise de estrutura de capital não se aplica a bancos.")
                    else:
                        st.subheader("Estrutura de Capital")
                        cols = ["Percentual Capital Terceiros", "Percentual Capital Próprio"]
                        data = []
                        for c in cols:
                            if c in df_filtrado.columns:
                                val = df_filtrado[c].iloc[0]
                                data.append({"Indicador": c, "Valor": formatar_percentual_brasil(val, 2) if pd.notna(val) else "N/A"})
                        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                        if len(data) == 2 and all(d["Valor"] != "N/A" for d in data):
                            valores = [df_filtrado["Percentual Capital Terceiros"].iloc[0], df_filtrado["Percentual Capital Próprio"].iloc[0]]
                            fig = px.pie(values=valores, names=["Capital Terceiros", "Capital Próprio"], title="Composição do Capital")
                            st.plotly_chart(fig, use_container_width=True)

                with sub_tabs[3]:
                    if is_bank:
                        st.info("ℹ️ Análise de custo de capital não se aplica a bancos.")
                    else:
                        st.subheader("Custo de Capital")
                        cols = ["ki", "ke", "wacc"]
                        data = []
                        for c in cols:
                            if c in df_filtrado.columns:
                                val = df_filtrado[c].iloc[0]
                                data.append({"Indicador": c, "Valor": formatar_percentual_brasil(val, 2) if pd.notna(val) else "N/A"})
                        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

                with sub_tabs[4]:
                    if is_bank:
                        st.info("ℹ️ Lucro Econômico não se aplica a bancos.")
                    else:
                        st.subheader("Lucro Econômico")
                        cols = ["Lucro Econômico 1", "Lucro Econômico 2"]
                        data = []
                        for c in cols:
                            if c in df_filtrado.columns:
                                val = df_filtrado[c].iloc[0]
                                data.append({"Indicador": c, "Valor": formatar_moeda_brasil_correta(val) if pd.notna(val) else "N/A"})
                        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

                with sub_tabs[5]:
                    st.subheader("💵 Fluxo de Caixa Operacional")
                    if 'Caixa Líquido Atividades Operacionais' in df_filtrado.columns:
                        val = df_filtrado['Caixa Líquido Atividades Operacionais'].iloc[0]
                        if pd.notna(val):
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Caixa Operacional", formatar_moeda_brasil_correta(val))
                            lucro = df_filtrado["Lucro/Prejuízo Consolidado do Período"].iloc[0] if pd.notna(df_filtrado["Lucro/Prejuízo Consolidado do Período"].iloc[0]) else 0
                            if lucro != 0:
                                col2.metric("Caixa/Lucro", f"{(val / lucro) * 100:.1f}%")
                            if not is_bank:
                                ebitda = df_filtrado["EBITDA"].iloc[0] if "EBITDA" in df_filtrado.columns and pd.notna(df_filtrado["EBITDA"].iloc[0]) else 0
                                if ebitda != 0:
                                    col3.metric("Caixa/EBITDA", f"{(val / ebitda) * 100:.1f}%")
                            st.success("✅ Geração Positiva" if val > 0 else "⚠️ Geração Negativa")
                        else:
                            st.warning("Dados não disponíveis para este ano.")
                    else:
                        st.warning("Coluna não encontrada.")

                with sub_tabs[6]:
                    st.subheader("Dados Brutos")
                    cols = ["Receita de Venda de Bens e/ou Serviços", "Resultado Bruto", "Resultado Antes do Resultado Financeiro e dos Tributos",
                            "Lucro/Prejuízo Consolidado do Período", "Despesas Financeiras", "Pagamento de Dividendos", "Ativo Total",
                            "Patrimônio Líquido Consolidado", "Empréstimos e Financiamentos - Circulante", "Empréstimos e Financiamentos - Não Circulante",
                            "Caixa Líquido Atividades Operacionais"]
                    if is_bank:
                        cols.append("Resultado Abrangente do Período")
                    if 'Depreciação e Amortização' in df_filtrado.columns:
                        cols.append("Depreciação e Amortização")
                    data = {}
                    for c in cols:
                        if c in df_filtrado.columns:
                            val = df_filtrado[c].iloc[0]
                            data[c] = formatar_moeda_brasil_correta(val) if pd.notna(val) else "N/A"
                    st.dataframe(pd.DataFrame.from_dict(data, orient='index', columns=['Valor']), use_container_width=True)

        # --- Aba Evolução Temporal ---
        with tab_evolucao:
            st.subheader("Evolução Temporal")
            if len(df_empresa_todos_anos) > 1:
                is_bank_series = df_empresa_todos_anos['is_bank'].iloc[0] if 'is_bank' in df_empresa_todos_anos.columns else False
                col1, col2 = st.columns(2)
                with col1:
                    fig = go.Figure()
                    inds = ['ROE', 'ROA'] if is_bank_series else ['ROE', 'ROA', 'ROI', 'Margem Líquida']
                    colors = ['#1f77b4','#ff7f0e','#2ca02c','#d62728']
                    for i, ind in enumerate(inds):
                        if ind in df_empresa_todos_anos.columns:
                            d = df_empresa_todos_anos[df_empresa_todos_anos[ind].notna()]
                            if not d.empty:
                                fig.add_trace(go.Scatter(x=d['Ano'], y=d[ind], mode='lines+markers', name=ind,
                                                         line=dict(color=colors[i % len(colors)], width=3), marker=dict(size=8)))
                    fig.update_layout(title='Rentabilidade', yaxis_tickformat=',.2%', height=400)
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    if not is_bank_series:
                        fig = go.Figure()
                        inds = ['Percentual Capital Terceiros', 'Percentual Capital Próprio']
                        colors = ['#e74c3c','#2ecc71']
                        for i, ind in enumerate(inds):
                            if ind in df_empresa_todos_anos.columns:
                                d = df_empresa_todos_anos[df_empresa_todos_anos[ind].notna()]
                                if not d.empty:
                                    fig.add_trace(go.Scatter(x=d['Ano'], y=d[ind], mode='lines+markers', name=ind,
                                                             line=dict(color=colors[i], width=3), marker=dict(size=8),
                                                             stackgroup='one' if i==0 else None))
                        fig.update_layout(title='Estrutura de Capital', yaxis_tickformat=',.2%', height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        if 'PL Médio' in df_empresa_todos_anos.columns:
                            fig = px.line(df_empresa_todos_anos, x='Ano', y='PL Médio', title='PL Médio')
                            fig.update_layout(yaxis_tickformat=',.0f')
                            st.plotly_chart(fig, use_container_width=True)
                if not is_bank_series:
                    col3, col4 = st.columns(2)
                    with col3:
                        fig = go.Figure()
                        inds = ['ki', 'ke', 'wacc']
                        names = ['Custo da Dívida (ki)', 'Custo do Capital Próprio (ke)', 'WACC']
                        colors = ['#9b59b6','#3498db','#f39c12']
                        for i, ind in enumerate(inds):
                            if ind in df_empresa_todos_anos.columns:
                                d = df_empresa_todos_anos[df_empresa_todos_anos[ind].notna()]
                                if not d.empty:
                                    fig.add_trace(go.Scatter(x=d['Ano'], y=d[ind], mode='lines+markers', name=names[i],
                                                             line=dict(color=colors[i], width=3), marker=dict(size=8)))
                        fig.update_layout(title='Custo de Capital', yaxis_tickformat=',.2%', height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    with col4:
                        fig = go.Figure()
                        inds = ['Margem Bruta', 'Margem Operacional', 'Margem Líquida']
                        colors = ['#16a085','#27ae60','#2980b9']
                        for i, ind in enumerate(inds):
                            if ind in df_empresa_todos_anos.columns:
                                d = df_empresa_todos_anos[df_empresa_todos_anos[ind].notna()]
                                if not d.empty:
                                    fig.add_trace(go.Scatter(x=d['Ano'], y=d[ind], mode='lines+markers', name=ind,
                                                             line=dict(color=colors[i], width=3), marker=dict(size=8)))
                        fig.update_layout(title='Margens', yaxis_tickformat=',.2%', height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    st.subheader("💰 Lucro Econômico e EBITDA")
                    col5, col6 = st.columns(2)
                    with col5:
                        fig = go.Figure()
                        inds = ['Lucro Econômico 1', 'Lucro Econômico 2']
                        colors = ['#e74c3c','#3498db']
                        for i, ind in enumerate(inds):
                            if ind in df_empresa_todos_anos.columns:
                                d = df_empresa_todos_anos[df_empresa_todos_anos[ind].notna()]
                                if not d.empty:
                                    fig.add_trace(go.Scatter(x=d['Ano'], y=d[ind], mode='lines+markers', name=ind,
                                                             line=dict(color=colors[i], width=3), marker=dict(size=8)))
                        fig.update_layout(title='Lucro Econômico', yaxis_tickformat=',.0f', height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    with col6:
                        fig = go.Figure()
                        inds = ['EBITDA', 'Resultado Antes do Resultado Financeiro e dos Tributos']
                        names = ['EBITDA', 'Resultado Operacional']
                        colors = ['#2ecc71','#34495e']
                        for i, ind in enumerate(inds):
                            if ind in df_empresa_todos_anos.columns:
                                d = df_empresa_todos_anos[df_empresa_todos_anos[ind].notna()]
                                if not d.empty:
                                    fig.add_trace(go.Scatter(x=d['Ano'], y=d[ind], mode='lines+markers', name=names[i],
                                                             line=dict(color=colors[i], width=3), marker=dict(size=8)))
                        fig.update_layout(title='EBITDA vs Resultado', yaxis_tickformat=',.0f', height=400)
                        st.plotly_chart(fig, use_container_width=True)

                st.subheader("💸 Fluxo de Caixa Operacional")
                if 'Caixa Líquido Atividades Operacionais' in df_empresa_todos_anos.columns:
                    col7, col8 = st.columns(2)
                    with col7:
                        fig = px.line(df_empresa_todos_anos, x='Ano', y='Caixa Líquido Atividades Operacionais', title='Caixa Operacional')
                        fig.update_layout(yaxis_tickformat=',.0f')
                        st.plotly_chart(fig, use_container_width=True)
                    with col8:
                        df_comp = df_empresa_todos_anos[df_empresa_todos_anos['Caixa Líquido Atividades Operacionais'].notna() &
                                                        df_empresa_todos_anos['Lucro/Prejuízo Consolidado do Período'].notna()]
                        if not df_comp.empty:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=df_comp['Ano'], y=df_comp['Caixa Líquido Atividades Operacionais'],
                                                     mode='lines+markers', name='Caixa Operacional', line=dict(color='#27ae60', width=3)))
                            fig.add_trace(go.Scatter(x=df_comp['Ano'], y=df_comp['Lucro/Prejuízo Consolidado do Período'],
                                                     mode='lines+markers', name='Lucro Líquido', line=dict(color='#e74c3c', width=3)))
                            fig.update_layout(title='Caixa vs Lucro', yaxis_tickformat=',.0f', height=400)
                            st.plotly_chart(fig, use_container_width=True)

                st.subheader("📋 Resumo Evolução")
                inds = ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio', 'Lucro Econômico 1', 'EBITDA', 'Caixa Líquido Atividades Operacionais'] if not is_bank_series else ['ROE', 'ROA', 'Margem Bruta', 'Margem Operacional', 'Resultado Abrangente do Período', 'PL Médio', 'Caixa Líquido Atividades Operacionais']
                df_resumo = df_empresa_todos_anos[['Ano'] + [c for c in inds if c in df_empresa_todos_anos.columns]]
                for c in df_resumo.columns:
                    if c != 'Ano':
                        if c in ['ROE','ROA','ROI','Margem Líquida','wacc','Percentual Capital Próprio','Margem Bruta','Margem Operacional']:
                            df_resumo[c] = df_resumo[c].apply(lambda x: formatar_percentual_brasil(x, 2) if pd.notna(x) else 'N/A')
                        else:
                            df_resumo[c] = df_resumo[c].apply(lambda x: formatar_moeda_brasil_correta(x) if pd.notna(x) else 'N/A')
                st.dataframe(df_resumo, use_container_width=True)
            else:
                st.info("São necessários dados de múltiplos anos.")

        # --- Aba Dividendos (CORRIGIDA) ---
        with tab_dividendos:
            st.subheader("💰 Dividendos / JCP Pagos")

            # 1. Tentar buscar do Yahoo Finance (para exibir os dados históricos, se disponível)
            df_div_yahoo = buscar_dividendos_historicos(ticker_selecionado)

            if df_div_yahoo is not None and not df_div_yahoo.empty:
                # Dados do Yahoo – exibir como antes
                stats = calcular_estatisticas_dividendos(df_div_yahoo)
                st.subheader(f"📊 Histórico de Dividendos (Yahoo) - {ticker_selecionado}")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Pago (desde 2010)", f"R$ {stats['total_dividendos']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                col2.metric("Média Anual", f"R$ {stats['media_anual']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                col3.metric("Último Provento", f"R$ {stats['ultimo_dividendo']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), 
                           help=f"Data: {stats['data_ultimo'].strftime('%d/%m/%Y') if stats['data_ultimo'] else 'N/A'}")
                cotacao = buscar_cotacao_atual(ticker_selecionado)
                dy = None
                if cotacao and cotacao['cotacao'] > 0:
                    data_limite = datetime.now() - timedelta(days=365)
                    div_12m = df_div_yahoo[df_div_yahoo['Data'] >= data_limite]
                    if not div_12m.empty:
                        total_12m = div_12m['Dividendo'].sum()
                        dy = (total_12m / cotacao['cotacao']) * 100
                col4.metric("Dividend Yield (12M)", formatar_percentual_brasil(dy/100) if dy is not None else "N/A")
                
                st.markdown("---")
                df_anual = df_div_yahoo.groupby('Ano')['Dividendo'].sum().reset_index()
                df_anual.columns = ['Ano', 'Total']
                fig = px.bar(df_anual, x='Ano', y='Total', title=f"Proventos por Ano - {ticker_selecionado}")
                fig.update_layout(yaxis_tickformat=',.2f')
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("📋 Histórico Detalhado")
                display = df_div_yahoo[['Data', 'Dividendo']].copy()
                display.columns = ['Data (Ex)', 'Valor (R$)']
                display['Valor (R$)'] = display['Valor (R$)'].apply(
                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
                display['Data (Ex)'] = display['Data (Ex)'].dt.strftime('%d/%m/%Y')
                st.dataframe(display.sort_values('Data (Ex)', ascending=False), use_container_width=True)

            else:
                # 2. Fallback: Dados da DFC – MOSTRAR APENAS TOTAIS
                st.info("ℹ️ Dados de dividendos do Yahoo Finance não disponíveis. Exibindo valores totais pagos conforme a DFC.")
                
                if 'Pagamento de Dividendos' in df_empresa_todos_anos.columns:
                    df_empresa_div = df_empresa_todos_anos[['Ano', 'Pagamento de Dividendos']].copy()
                    df_empresa_div = df_empresa_div[df_empresa_div['Pagamento de Dividendos'].notna()]
                    df_empresa_div['Total Pago (R$)'] = df_empresa_div['Pagamento de Dividendos'] * 1000
                    
                    if not df_empresa_div.empty:
                        st.subheader(f"📊 Proventos Totais Pagos (R$) - {ticker_selecionado}")
                        fig = px.bar(df_empresa_div, x='Ano', y='Total Pago (R$)', 
                                     title="Total de Dividendos/JCP Pagos por Ano (Fonte: DFC)")
                        fig.update_layout(yaxis_tickformat=',.0f')
                        st.plotly_chart(fig, use_container_width=True)
                        
                        st.subheader("📋 Detalhamento Anual")
                        display = df_empresa_div[['Ano', 'Total Pago (R$)']].copy()
                        display['Total Pago (R$)'] = display['Total Pago (R$)'].apply(
                            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else "N/A"
                        )
                        st.dataframe(display, use_container_width=True)
                        
                        total_pago = df_empresa_div['Total Pago (R$)'].sum()
                        media_anual = df_empresa_div['Total Pago (R$)'].mean()
                        col1, col2 = st.columns(2)
                        col1.metric("Total Pago (período)", f"R$ {total_pago:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                        col2.metric("Média Anual (Total)", f"R$ {media_anual:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                        
                        ultimo_ano = df_empresa_div['Ano'].max()
                        ultimo_total = df_empresa_div[df_empresa_div['Ano'] == ultimo_ano]['Total Pago (R$)'].iloc[0] if not df_empresa_div.empty else None
                        if ultimo_total and ultimo_total > 0:
                            st.metric(f"Total Pago no último ano ({ultimo_ano})", f"R$ {ultimo_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    else:
                        st.warning("Não há dados de pagamento de dividendos/JCP nas demonstrações financeiras para esta empresa.")
                else:
                    st.warning("Coluna 'Pagamento de Dividendos' não encontrada no arquivo de dados.")

        # --- Aba Simulação de Investimento ---
        with tab_simulacao:
            st.subheader("💵 Simulação de Investimento por Lotes")
            col_data, col_lote = st.columns(2)
            with col_data:
                data_compra = st.date_input("Data da compra", value=datetime(2015,1,1).date(),
                                            min_value=datetime(2000,1,1).date(),
                                            max_value=datetime.now().date() - timedelta(days=365))
            with col_lote:
                lote = st.selectbox("Tamanho do lote:", [100, 1000, 10000], index=0, format_func=lambda x: f"{x} ações")
            if st.button("Executar Simulação"):
                res = simular_investimento_lotes(ticker_selecionado, data_compra, lote)
                if res and 'error' in res:
                    st.error(f"❌ {res['message']}")
                elif res:
                    if res.get('sem_dividendos', False):
                        st.warning("⚠️ Nenhum provento registrado no período. O ganho reflete apenas valorização.")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Valor Investido", f"R$ {res['valor_investido']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), help=f"Preço compra: R$ {res['preco_compra']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    col2.metric("Valor Atual", f"R$ {res['valor_investido_atual']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), help=f"Preço atual: R$ {res['preco_atual']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    col3.metric("Total Dividendos", f"R$ {res['total_dividendos_recebidos']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    col4.metric("Ganho Total", f"R$ {res['ganho_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), delta=f"Rentabilidade: {res['rentabilidade_total_percentual']:,.2f}%".replace(".", ","))
                    st.markdown("---")
                    col_rent1, col_rent2, col_rent3 = st.columns(3)
                    col_rent1.metric("Apreciação", f"{res['rentabilidade_preco_percentual']:,.2f}%".replace(".", ","))
                    col_rent2.metric("Dividendos", f"{res['rentabilidade_dividendos_percentual']:,.2f}%".replace(".", ","))
                    col_rent3.metric("Total", f"{res['rentabilidade_total_percentual']:,.2f}%".replace(".", ","))
                else:
                    st.error("❌ Não foi possível realizar a simulação. Dados de preço não encontrados para o período.")

    else:
        st.warning("Empresa não encontrada na base de dados.")

# ==============================
# MODO: ANÁLISE SETORIAL
# ==============================
elif modo_analise == "🏭 Análise Setorial":
    st.header(f"🏭 Análise Setorial - {setor_selecionado}")
    if not df_setor_todos_anos.empty:
        tab_atual, tab_evol = st.tabs(["📊 Análise do Ano", "📈 Evolução Temporal"])
        with tab_atual:
            st.subheader(f"Ano {ano_selecionado}")
            if not df_filtrado.empty:
                is_bank_setor = setor_selecionado.lower() in ['bancos', 'instituição financeira', 'financeiro']
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Empresas", df_filtrado["Ticker"].nunique())
                col2.metric("Receita Total", formatar_moeda_brasil_correta(df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum(), 2))
                col3.metric("Lucro Total", formatar_moeda_brasil_correta(df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum(), 2))
                col4.metric("PL Total", formatar_moeda_brasil_correta(df_filtrado["Patrimônio Líquido Consolidado"].sum(), 2))
                st.divider()
                st.subheader("Top 10 ROE")
                top = df_filtrado[df_filtrado["ROE"].notna()].nlargest(10, "ROE")[["Ticker", "ROE"]]
                if not top.empty:
                    fig = px.bar(top, x="Ticker", y="ROE", title="ROE no Setor")
                    fig.update_layout(yaxis_tickformat=',.2%')
                    st.plotly_chart(fig, use_container_width=True)
                if not is_bank_setor:
                    st.subheader("Estrutura de Capital")
                    df_est = df_filtrado[df_filtrado["Percentual Capital Próprio"].notna()].nlargest(15, "Patrimônio Líquido Consolidado")
                    if not df_est.empty:
                        fig = px.bar(df_est, x="Ticker", y=["Percentual Capital Terceiros", "Percentual Capital Próprio"],
                                     title="Estrutura de Capital", barmode='stack')
                        fig.update_layout(yaxis_tickformat=',.2%')
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Estrutura de capital não se aplica a bancos.")
                st.subheader("Ranking de Rentabilidade")
                cols = ["Ticker", "ROE", "ROA", "ROI", "Margem Líquida"] if not is_bank_setor else ["Ticker", "ROE", "ROA"]
                df_rank = df_filtrado[df_filtrado["ROE"].notna() & df_filtrado["ROA"].notna()].nlargest(15, "ROE")[cols]
                if not df_rank.empty:
                    fmt_cols = [c for c in cols if c in ['ROE','ROA','ROI','Margem Líquida']]
                    st.dataframe(formatar_dataframe_percentual(df_rank, fmt_cols), use_container_width=True)
            else:
                st.warning(f"Não há dados para {setor_selecionado} em {ano_selecionado}.")

        with tab_evol:
            st.subheader("Evolução Temporal do Setor")
            if len(df_setor_todos_anos['Ano'].unique()) > 1:
                is_bank_setor = setor_selecionado.lower() in ['bancos', 'instituição financeira', 'financeiro']
                candidatos = ['ROE','ROA','ROI','Margem Líquida','wacc','Percentual Capital Próprio','Lucro Econômico 1','EBITDA'] if not is_bank_setor else ['ROE','ROA','Margem Bruta','Margem Operacional','Resultado Abrangente do Período','PL Médio']
                indicadores = [c for c in candidatos if c in df_setor_todos_anos.columns]
                if not indicadores:
                    st.warning("Nenhum indicador disponível para evolução.")
                else:
                    df_evol = df_setor_todos_anos.groupby('Ano')[indicadores].median().reset_index()
                    col1, col2 = st.columns(2)
                    with col1:
                        fig = go.Figure()
                        rent = ['ROE','ROA','ROI'] if not is_bank_setor else ['ROE','ROA']
                        for i, ind in enumerate(rent):
                            if ind in df_evol.columns:
                                d = df_evol[df_evol[ind].notna()]
                                if not d.empty:
                                    fig.add_trace(go.Scatter(x=d['Ano'], y=d[ind], mode='lines+markers', name=ind,
                                                             line=dict(color=['#1f77b4','#ff7f0e','#2ca02c'][i], width=3)))
                        fig.update_layout(title='Rentabilidade (Mediana)', yaxis_tickformat=',.2%', height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    with col2:
                        if not is_bank_setor:
                            fig = go.Figure()
                            for ind in ['Percentual Capital Próprio', 'wacc']:
                                if ind in df_evol.columns:
                                    d = df_evol[df_evol[ind].notna()]
                                    if not d.empty:
                                        fig.add_trace(go.Scatter(x=d['Ano'], y=d[ind], mode='lines+markers', name=ind,
                                                                 line=dict(color=['#2ecc71','#f39c12'][0 if ind=='Percentual Capital Próprio' else 1], width=3)))
                            fig.update_layout(title='Estrutura e Custo (Mediana)', yaxis_tickformat=',.2%', height=400)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            if 'PL Médio' in df_evol.columns:
                                fig = px.line(df_evol, x='Ano', y='PL Médio', title='PL Médio (Mediana)')
                                fig.update_layout(yaxis_tickformat=',.0f')
                                st.plotly_chart(fig, use_container_width=True)
                    if not is_bank_setor and 'Lucro Econômico 1' in df_evol.columns and 'EBITDA' in df_evol.columns:
                        st.subheader("Lucro Econômico e EBITDA")
                        col3, col4 = st.columns(2)
                        with col3:
                            fig = px.line(df_evol, x='Ano', y='Lucro Econômico 1', title='Lucro Econômico (Mediana)')
                            fig.update_layout(yaxis_tickformat=',.0f')
                            st.plotly_chart(fig, use_container_width=True)
                        with col4:
                            fig = px.line(df_evol, x='Ano', y='EBITDA', title='EBITDA (Mediana)')
                            fig.update_layout(yaxis_tickformat=',.0f')
                            st.plotly_chart(fig, use_container_width=True)
                    st.subheader("Resumo da Evolução")
                    for c in df_evol.columns:
                        if c != 'Ano':
                            if c in ['ROE','ROA','ROI','Margem Líquida','wacc','Percentual Capital Próprio','Margem Bruta','Margem Operacional']:
                                df_evol[c] = df_evol[c].apply(lambda x: formatar_percentual_brasil(x, 2) if pd.notna(x) else 'N/A')
                            else:
                                df_evol[c] = df_evol[c].apply(lambda x: formatar_moeda_brasil_correta(x) if pd.notna(x) else 'N/A')
                    st.dataframe(df_evol, use_container_width=True)
                    if ano_selecionado in df_setor_todos_anos['Ano'].values:
                        df_ano = df_setor_todos_anos[df_setor_todos_anos['Ano'] == ano_selecionado]
                        if not df_ano.empty and 'ROE' in df_ano.columns:
                            fig = px.box(df_ano, y='ROE', title=f'Distribuição do ROE no Setor - {ano_selecionado}')
                            fig.update_layout(yaxis_tickformat=',.2%')
                            st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("São necessários dados de múltiplos anos.")

# ==============================
# RODAPÉ
# ==============================
st.divider()
st.caption(f"📊 Dados atualizados para {ano_selecionado} | Total de empresas: {df['Ticker'].nunique()}")
st.sidebar.divider()
st.sidebar.info("Dashboard baseado em dados da CVM até 2025. Suporte a bancos, dividendos e simulações.")
