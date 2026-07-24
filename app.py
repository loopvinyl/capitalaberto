# ==============================================================
# 📊 INDICADORES FINANCEIROS - APP STREAMLIT
# Base: dff_2010_2025.xlsx (gerado pelos Scripts 1, 2 e 3)
# Suporte a Bancos e Não Bancos (Vellani, 2024)
# ==============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
import yfinance as yf
from datetime import datetime
import locale

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
# FUNÇÕES DE FORMATAÇÃO (MOEDA, NÚMERO, PERCENTUAL)
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
# FUNÇÕES AUXILIARES (VALUATION, COTAÇÃO, GRÁFICO)
# ==============================
def calcular_valuation_lucro_economico_selic(lucro_economico, selic_percentual=15):
    if lucro_economico and lucro_economico > 0:
        return lucro_economico / (selic_percentual / 100)
    return None

def buscar_cotacao_atual(ticker):
    try:
        ticker_yf = f"{ticker}.SA"
        acao = yf.Ticker(ticker_yf)
        info = acao.info
        cotacao = info.get('regularMarketPrice') or info.get('currentPrice')
        if cotacao:
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
    except Exception as e:
        st.warning(f"⚠️ Não foi possível buscar cotação para {ticker}: {str(e)}")
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
# CONFIGURAÇÕES INICIAIS DO APP
# ==============================
st.set_page_config(page_title="Indicadores Financeiros", layout="wide")
st.title("📊 Análise das Demonstrações Financeiras")

# ==============================
# LEITURA DE DADOS (CACHE)
# ==============================
@st.cache_data
def load_data():
    possible_paths = [
        "/content/dff_2010_2025.xlsx",
        "dff_2010_2025.xlsx",
        "./data/dff_2010_2025.xlsx"
    ]
    data_path = None
    for path in possible_paths:
        if os.path.exists(path):
            data_path = path
            break

    if data_path is None:
        st.error(
            "❌ Arquivo 'dff_2010_2025.xlsx' não encontrado.\n\n"
            "Coloque o arquivo na mesma pasta do app ou em /content/ (se estiver no Colab),\n"
            "ou salve em ./data/dff_2010_2025.xlsx.\n\n"
            "Caminhos verificados:\n- " + "\n- ".join(possible_paths)
        )
        st.stop()

    df = pd.read_excel(data_path)
    df.columns = [c.strip() for c in df.columns]

    # Normalização de nomes
    if 'Pagamento de Dividendos (ou Proventos)' in df.columns:
        df.rename(columns={'Pagamento de Dividendos (ou Proventos)': 'Pagamento de Dividendos'}, inplace=True)

    # Identificar setor bancário
    if 'SETOR_ATIV' in df.columns:
        df['is_bank'] = df['SETOR_ATIV'].str.contains('Bancos|Financeiro|Instituição Financeira', case=False, na=False)
    else:
        df['is_bank'] = False

    df = df.sort_values(['Ticker', 'Ano']).reset_index(drop=True)

    # Médias
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

    # ROA e ROE (para todos)
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

    # ROI (apenas não bancos)
    df["ROI"] = np.where(
        (df["Investimento Médio"] > 0) & (~df['is_bank']),
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] / df["Investimento Médio"],
        np.nan
    )

    # Margens (algumas apenas não bancos)
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

    # Estrutura de capital (apenas não bancos)
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

    # Custo de capital (apenas não bancos)
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

    # EBITDA (apenas não bancos)
    nome_coluna_da = None
    for col in df.columns:
        if 'depreciação' in col.lower() and 'amortização' in col.lower():
            nome_coluna_da = col
            break
    if nome_coluna_da:
        depreciacao_amortizacao = abs(df[nome_coluna_da].fillna(0))
        df["EBITDA"] = np.where(
            ~df['is_bank'] & df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna(),
            df["Resultado Antes do Resultado Financeiro e dos Tributos"] + depreciacao_amortizacao,
            np.nan
        )
    else:
        df["EBITDA"] = np.where(~df['is_bank'], df["Resultado Antes do Resultado Financeiro e dos Tributos"], np.nan)

    # Lucro econômico (apenas não bancos)
    df["Lucro Econômico 1"] = np.where(
        (~df['is_bank']) &
        (df["ROI"].notna()) & (df["wacc"].notna()) & (df["Investimento Médio"].notna()),
        (df["ROI"] - df["wacc"]) * df["Investimento Médio"],
        np.nan
    )
    df["Lucro Econômico 2"] = np.where(
        (~df['is_bank']) &
        (df["Resultado Antes do Resultado Financeiro e dos Tributos"].notna()) &
        (df["wacc"].notna()) & (df["Investimento Médio"].notna()),
        df["Resultado Antes do Resultado Financeiro e dos Tributos"] - (df["wacc"] * df["Investimento Médio"]),
        np.nan
    )
    df["Diferença Lucro Econômico"] = abs(df["Lucro Econômico 1"] - df["Lucro Econômico 2"])

    # Alavancagem (apenas não bancos)
    df["Alavancagem Eficaz"] = np.where(
        (~df['is_bank']) &
        (df["ROE"].notna()) & (df["ROA"].notna()) & (df["ROI"].notna()),
        (df["ROE"] > df["ROA"]) & (df["ROE"] > df["ROI"]),
        False
    )

    return df

# Carregar dados
df = load_data()

# ==============================
# SIDEBAR - FILTROS
# ==============================
st.sidebar.header("🔧 Filtros Principais")
modo_analise = st.sidebar.radio(
    "Modo de Análise:",
    ["🏆 Dados Gerais", "📈 Visão por Empresa", "🏭 Análise Setorial"]
)
anos_disponiveis = sorted(df["Ano"].unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Selecione o Ano:", anos_disponiveis)

if modo_analise == "📈 Visão por Empresa":
    ticker_selecionado = st.sidebar.selectbox(
        "Selecione a Empresa:",
        sorted(df["Ticker"].dropna().unique())
    )
    df_filtrado = df[(df["Ticker"] == ticker_selecionado) & (df["Ano"] == ano_selecionado)]
    df_empresa_todos_anos = df[df["Ticker"] == ticker_selecionado].sort_values("Ano")
elif modo_analise == "🏭 Análise Setorial":
    setor_selecionado = st.sidebar.selectbox(
        "Selecione o Setor:",
        sorted(df["SETOR_ATIV"].dropna().unique())
    )
    df_filtrado = df[(df["SETOR_ATIV"] == setor_selecionado) & (df["Ano"] == ano_selecionado)]
    df_setor_todos_anos = df[df["SETOR_ATIV"] == setor_selecionado].sort_values(["Ano", "Ticker"])
else:
    df_filtrado = df[df["Ano"] == ano_selecionado]

# ==============================
# MODO: DADOS GERAIS (RANKINGS)
# ==============================
if modo_analise == "🏆 Dados Gerais":
    st.header(f"🏆 Ano mais recente publicado: {ano_selecionado}")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Empresas Analisadas", df_filtrado["Ticker"].nunique())
    with col2:
        st.metric("Setores Representados", df_filtrado["SETOR_ATIV"].nunique())
    with col3:
        receita_total = df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum()
        st.metric("Receita Total", formatar_moeda_brasil_correta(receita_total, 2))
    with col4:
        lucro_total = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum()
        st.metric("Lucro Total", formatar_moeda_brasil_correta(lucro_total, 2))
    st.divider()

    rank_tab1, rank_tab2, rank_tab3, rank_tab4 = st.tabs(["📈 Rentabilidade", "💰 Lucro e Receita", "🏛️ Solidez", "📊 Eficiência"])

    with rank_tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 15 Empresas por ROE")
            roe_ranking = df_filtrado[df_filtrado["ROE"].notna()].nlargest(15, "ROE")[["Ticker", "SETOR_ATIV", "ROE"]]
            if not roe_ranking.empty:
                fig_roe_rank = px.bar(roe_ranking, x="Ticker", y="ROE", color="SETOR_ATIV", title="Ranking de ROE")
                fig_roe_rank.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_roe_rank, use_container_width=True)
            else:
                st.warning("Não há dados de ROE disponíveis para ranking")
        with col2:
            st.subheader("Top 15 Empresas por ROA")
            roa_ranking = df_filtrado[df_filtrado["ROA"].notna()].nlargest(15, "ROA")[["Ticker", "SETOR_ATIV", "ROA"]]
            if not roa_ranking.empty:
                fig_roa_rank = px.bar(roa_ranking, x="Ticker", y="ROA", color="SETOR_ATIV", title="Ranking de ROA")
                fig_roa_rank.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_roa_rank, use_container_width=True)
            else:
                st.warning("Não há dados de ROA disponíveis para ranking")
        st.subheader("📋 Tabela de Rentabilidade - Top 20")
        rentabilidade_consolidado = df_filtrado[
            df_filtrado["ROE"].notna() & df_filtrado["ROA"].notna()
        ].nlargest(20, "ROE")[["Ticker", "SETOR_ATIV", "ROE", "ROA", "ROI", "Margem Líquida"]]
        if not rentabilidade_consolidado.empty:
            rentabilidade_formatado = formatar_dataframe_percentual(
                rentabilidade_consolidado, ['ROE', 'ROA', 'ROI', 'Margem Líquida']
            )
            st.dataframe(rentabilidade_formatado, use_container_width=True)
        else:
            st.warning("Não há dados suficientes para exibir a tabela consolidada")

    with rank_tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 15 Empresas por Lucro Líquido")
            lucro_ranking = df_filtrado.nlargest(15, "Lucro/Prejuízo Consolidado do Período")[["Ticker", "SETOR_ATIV", "Lucro/Prejuízo Consolidado do Período"]]
            if not lucro_ranking.empty:
                lucro_ranking["Lucro (R$)"] = lucro_ranking["Lucro/Prejuízo Consolidado do Período"] * 1000 / 1e9
                fig_lucro_rank = px.bar(lucro_ranking, x="Ticker", y="Lucro (R$)", color="SETOR_ATIV", title="Ranking por Lucro Líquido")
                fig_lucro_rank.update_layout(yaxis_tickformat=',.2f')
                st.plotly_chart(fig_lucro_rank, use_container_width=True)
                lucro_ranking["Lucro"] = lucro_ranking["Lucro/Prejuízo Consolidado do Período"].apply(formatar_moeda_brasil_correta)
                st.dataframe(lucro_ranking[["Ticker", "SETOR_ATIV", "Lucro"]], use_container_width=True)
            else:
                st.warning("Não há dados de lucro disponíveis para ranking")
        with col2:
            st.subheader("Top 15 Empresas por Receita")
            receita_ranking = df_filtrado.nlargest(15, "Receita de Venda de Bens e/ou Serviços")[["Ticker", "SETOR_ATIV", "Receita de Venda de Bens e/ou Serviços"]]
            if not receita_ranking.empty:
                receita_ranking["Receita (R$)"] = receita_ranking["Receita de Venda de Bens e/ou Serviços"] * 1000 / 1e9
                fig_receita_rank = px.bar(receita_ranking, x="Ticker", y="Receita (R$)", color="SETOR_ATIV", title="Ranking por Receita")
                fig_receita_rank.update_layout(yaxis_tickformat=',.2f')
                st.plotly_chart(fig_receita_rank, use_container_width=True)
                receita_ranking["Receita"] = receita_ranking["Receita de Venda de Bens e/ou Serviços"].apply(formatar_moeda_brasil_correta)
                st.dataframe(receita_ranking[["Ticker", "SETOR_ATIV", "Receita"]], use_container_width=True)
            else:
                st.warning("Não há dados de receita disponíveis para ranking")

    with rank_tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 15 Empresas por Patrimônio Líquido")
            pl_ranking = df_filtrado.nlargest(15, "Patrimônio Líquido Consolidado")[["Ticker", "SETOR_ATIV", "Patrimônio Líquido Consolidado"]]
            if not pl_ranking.empty:
                pl_ranking["PL (R$)"] = pl_ranking["Patrimônio Líquido Consolidado"] * 1000 / 1e9
                fig_pl_rank = px.bar(pl_ranking, x="Ticker", y="PL (R$)", color="SETOR_ATIV", title="Ranking de Patrimônio Líquido")
                fig_pl_rank.update_layout(yaxis_tickformat=',.2f')
                st.plotly_chart(fig_pl_rank, use_container_width=True)
                pl_ranking["Patrimônio Líquido"] = pl_ranking["Patrimônio Líquido Consolidado"].apply(formatar_moeda_brasil_correta)
                st.dataframe(pl_ranking[["Ticker", "SETOR_ATIV", "Patrimônio Líquido"]], use_container_width=True)
            else:
                st.warning("Não há dados de patrimônio líquido disponíveis para ranking")
        with col2:
            st.subheader("Top 15 Empresas por ROI")
            roi_ranking = df_filtrado[df_filtrado["ROI"].notna()].nlargest(15, "ROI")[["Ticker", "SETOR_ATIV", "ROI"]]
            if not roi_ranking.empty:
                fig_roi_rank = px.bar(roi_ranking, x="Ticker", y="ROI", color="SETOR_ATIV", title="Ranking de ROI")
                fig_roi_rank.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_roi_rank, use_container_width=True)
            else:
                st.warning("Não há dados de ROI disponíveis para ranking")

    with rank_tab4:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 15 Empresas por Margem Líquida")
            margem_ranking = df_filtrado[df_filtrado["Margem Líquida"].notna()].nlargest(15, "Margem Líquida")[["Ticker", "SETOR_ATIV", "Margem Líquida"]]
            if not margem_ranking.empty:
                fig_margem_rank = px.bar(margem_ranking, x="Ticker", y="Margem Líquida", color="SETOR_ATIV", title="Ranking por Margem Líquida")
                fig_margem_rank.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_margem_rank, use_container_width=True)
            else:
                st.warning("Não há dados de margem líquida disponíveis para ranking")
        with col2:
            st.subheader("Empresas com Melhor WACC")
            wacc_ranking = df_filtrado[df_filtrado["wacc"].notna()].nsmallest(15, "wacc")[["Ticker", "SETOR_ATIV", "wacc"]]
            if not wacc_ranking.empty:
                fig_wacc_rank = px.bar(wacc_ranking, x="Ticker", y="wacc", color="SETOR_ATIV", title="Ranking por WACC (menor é melhor)")
                fig_wacc_rank.update_layout(yaxis_tickformat=',.2%')
                st.plotly_chart(fig_wacc_rank, use_container_width=True)
            else:
                st.warning("Não há dados de WACC disponíveis para ranking")

# ==============================
# MODO: VISÃO POR EMPRESA
# ==============================
elif modo_analise == "📈 Visão por Empresa":
    st.header(f"📊 Análise Detalhada - {ticker_selecionado}")
    if not df_empresa_todos_anos.empty:
        tab_atual, tab_evolucao = st.tabs(["📊 Análise do Ano", "📈 Evolução Temporal"])
        with tab_atual:
            st.subheader(f"Ano {ano_selecionado}")
            if not df_filtrado.empty:
                is_bank = df_filtrado['is_bank'].iloc[0] if 'is_bank' in df_filtrado.columns else False

                # KPIs
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    valor_roe = df_filtrado["ROE"].iloc[0]
                    st.metric("ROE", formatar_percentual_brasil(valor_roe, 2) if pd.notna(valor_roe) else "-")
                with col2:
                    valor_roa = df_filtrado["ROA"].iloc[0]
                    st.metric("ROA", formatar_percentual_brasil(valor_roa, 2) if pd.notna(valor_roa) else "-")
                with col3:
                    if not is_bank:
                        valor_roi = df_filtrado["ROI"].iloc[0]
                        st.metric("ROI", formatar_percentual_brasil(valor_roi, 2) if pd.notna(valor_roi) else "-")
                    else:
                        st.metric("ROI", "N/A (Banco)")
                with col4:
                    if not is_bank:
                        valor_wacc = df_filtrado["wacc"].iloc[0]
                        st.metric("WACC", formatar_percentual_brasil(valor_wacc, 2) if pd.notna(valor_wacc) else "-")
                    else:
                        st.metric("WACC", "N/A (Banco)")
                with col5:
                    if 'Caixa Líquido Atividades Operacionais' in df_filtrado.columns:
                        valor_caixa = df_filtrado['Caixa Líquido Atividades Operacionais'].iloc[0]
                        st.metric("Caixa Operacional", formatar_moeda_brasil_correta(valor_caixa) if pd.notna(valor_caixa) else "N/A")
                    else:
                        st.metric("Caixa Operacional*", "N/A")

                # Verificação Lucro Econômico (não bancos)
                if not is_bank:
                    st.subheader("🔍 Verificação: Lucro Econômico 1 vs 2")
                    lucro_eco1 = df_filtrado["Lucro Econômico 1"].iloc[0]
                    lucro_eco2 = df_filtrado["Lucro Econômico 2"].iloc[0]
                    if pd.notna(lucro_eco1) and pd.notna(lucro_eco2):
                        diferenca = abs(lucro_eco1 - lucro_eco2)
                        tolerancia = max(abs(lucro_eco1), abs(lucro_eco2)) * 0.001
                        if diferenca <= tolerancia:
                            st.success("✅ LUCRO ECONÔMICO 1 = LUCRO ECONÔMICO 2")
                            st.write(f"Lucro Econômico 1: {formatar_moeda_brasil_correta(lucro_eco1)}")
                            st.write(f"Lucro Econômico 2: {formatar_moeda_brasil_correta(lucro_eco2)}")
                            st.write(f"Diferença: {formatar_moeda_brasil_correta(diferenca)} (dentro da tolerância)")
                        else:
                            st.error("❌ LUCRO ECONÔMICO 1 ≠ LUCRO ECONÔMICO 2")
                            st.write(f"Lucro Econômico 1: {formatar_moeda_brasil_correta(lucro_eco1)}")
                            st.write(f"Lucro Econômico 2: {formatar_moeda_brasil_correta(lucro_eco2)}")
                            st.write(f"Diferença: {formatar_moeda_brasil_correta(diferenca)}")
                    else:
                        st.info("ℹ️ Dados de Lucro Econômico não disponíveis para verificação")

                # Análise de alavancagem (não bancos)
                if not is_bank:
                    st.subheader("🔍 Análise de Alavancagem")
                    if pd.notna(df_filtrado["Alavancagem Eficaz"].iloc[0]):
                        if df_filtrado["Alavancagem Eficaz"].iloc[0]:
                            st.success("✅ Alavancagem com Eficácia: SIM")
                            st.write(f"ROE ({formatar_percentual_brasil(df_filtrado['ROE'].iloc[0], 2)}) > ROA ({formatar_percentual_brasil(df_filtrado['ROA'].iloc[0], 2)})")
                        else:
                            st.warning("⚠️ Alavancagem com Eficácia: NÃO")
                    else:
                        st.info("ℹ️ Análise de alavancagem não disponível")
                else:
                    st.info("ℹ️ Análise de alavancagem não se aplica a bancos.")

                st.divider()

                # =============================================================
                # ABAS UNIFICADAS (7 abas sempre)
                # =============================================================
                tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
                    "📈 Rentabilidade",
                    "🏦 Valuation",
                    "🏛️ Estrutura Capital",
                    "💸 Custo Capital",
                    "📊 Lucro Econômico",
                    "💵 Fluxo de Caixa",
                    "📋 Dados Brutos"
                ])

                # --- ABA 1: RENTABILIDADE ---
                with tab1:
                    st.subheader("Indicadores de Rentabilidade")
                    if is_bank:
                        rentabilidade_cols = ["ROE", "ROA", "Margem Bruta", "Margem Operacional"]
                    else:
                        rentabilidade_cols = ["ROE", "ROA", "ROI", "Margem Bruta", "Margem Operacional", "Margem Líquida"]
                    rentabilidade_data = []
                    for col in rentabilidade_cols:
                        if col in df_filtrado.columns:
                            valor = df_filtrado[col].iloc[0]
                            if pd.notna(valor):
                                rentabilidade_data.append({"Indicador": col, "Valor": formatar_percentual_brasil(valor, 2), "Status": "✓"})
                            else:
                                rentabilidade_data.append({"Indicador": f"{col}*", "Valor": "Não calculado", "Status": "✗"})
                    if rentabilidade_data:
                        rentabilidade_df = pd.DataFrame(rentabilidade_data)
                        st.dataframe(rentabilidade_df[["Indicador", "Valor"]], use_container_width=True, hide_index=True)
                    else:
                        st.warning("Não há dados de rentabilidade disponíveis")

                # --- ABA 2: VALUATION (UNIFICADA) ---
                with tab2:
                    if is_bank:
                        # VALUATION PARA BANCOS
                        st.subheader("🏦 Valuation para Bancos")
                        resultado_abrangente = df_filtrado['Resultado Abrangente do Período'].iloc[0] if 'Resultado Abrangente do Período' in df_filtrado.columns else None
                        pl_medio = df_filtrado['PL Médio'].iloc[0] if 'PL Médio' in df_filtrado.columns else None
                        numero_acoes = None
                        if 'Numero_Acoes' in df_filtrado.columns and pd.notna(df_filtrado['Numero_Acoes'].iloc[0]):
                            numero_acoes = df_filtrado['Numero_Acoes'].iloc[0]
                        else:
                            dados_cotacao = buscar_cotacao_atual(ticker_selecionado)
                            if dados_cotacao and dados_cotacao.get('sharesOutstanding'):
                                numero_acoes = dados_cotacao['sharesOutstanding']

                        if resultado_abrangente and pl_medio and numero_acoes and numero_acoes > 0:
                            col_selic1, col_selic2 = st.columns([2, 1])
                            with col_selic1:
                                st.write("**Taxa de Desconto (SELIC):**")
                            with col_selic2:
                                selic_percentual = st.number_input("SELIC (%)", min_value=0.1, max_value=30.0, value=13.5, step=0.1, help="Taxa SELIC para cálculo do valuation de bancos")

                            lpa = resultado_abrangente / numero_acoes
                            vpa = pl_medio / numero_acoes
                            r = selic_percentual / 100
                            cotacao_esperada = (lpa - (vpa * r)) / r
                            dados_cotacao = buscar_cotacao_atual(ticker_selecionado)

                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Resultado Abrangente", formatar_moeda_brasil_correta(resultado_abrangente))
                            with col2:
                                st.metric("PL Médio", formatar_moeda_brasil_correta(pl_medio))
                            with col3:
                                st.metric("Nº de Ações", formatar_numero_brasil_correto(numero_acoes, 0))
                            with col4:
                                st.metric("Cotação Esperada", f"R$ {cotacao_esperada:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

                            st.info(f"""
                            **📊 Fórmula de Valuation para Bancos (Vellani, 2024):**

                            LPA = Resultado Abrangente ÷ Nº de Ações
                            LPA = {formatar_moeda_brasil_correta(resultado_abrangente)} ÷ {formatar_numero_brasil_correto(numero_acoes, 0)}
                            LPA = R$ {lpa:,.2f}

                            VPA = PL Médio ÷ Nº de Ações
                            VPA = {formatar_moeda_brasil_correta(pl_medio)} ÷ {formatar_numero_brasil_correto(numero_acoes, 0)}
                            VPA = R$ {vpa:,.2f}

                            Cotação Esperada = (LPA - (VPA × r)) / r
                            Cotação Esperada = ({lpa:,.2f} - ({vpa:,.2f} × {r:.3f})) / {r:.3f}
                            Cotação Esperada = R$ {cotacao_esperada:,.2f}
                            """)

                            if dados_cotacao:
                                st.subheader("📈 Comparação com Mercado")
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("Cotação Atual", f"R$ {dados_cotacao['cotacao']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                with col2:
                                    diferenca = ((dados_cotacao['cotacao'] - cotacao_esperada) / cotacao_esperada) * 100
                                    st.metric("Diferença", f"{diferenca:+.1f}%")
                                if diferenca > 20:
                                    st.error("🔴 Sobrevalorizado: cotação atual acima do valuation.")
                                elif diferenca < -20:
                                    st.success("🟢 Subvalorizado: cotação atual abaixo do valuation.")
                                else:
                                    st.info("🟡 Valuation próximo: cotação alinhada com fundamentos.")
                        else:
                            st.warning("Dados insuficientes para valuation de bancos. Necessário: Resultado Abrangente, PL Médio e Número de Ações.")
                    else:
                        # VALUATION PARA NÃO BANCOS (EBITDA + Lucro Econômico/SELIC)
                        st.subheader("📊 EBITDA - Geração de Caixa Operacional")
                        ebitda_valor = df_filtrado["EBITDA"].iloc[0] if "EBITDA" in df_filtrado.columns and pd.notna(df_filtrado["EBITDA"].iloc[0]) else None
                        resultado_operacional = df_filtrado["Resultado Antes do Resultado Financeiro e dos Tributos"].iloc[0] if pd.notna(df_filtrado["Resultado Antes do Resultado Financeiro e dos Tributos"].iloc[0]) else None
                        if ebitda_valor is not None and resultado_operacional is not None:
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("EBITDA", formatar_moeda_brasil_correta(ebitda_valor))
                            with col2:
                                st.metric("Resultado Operacional", formatar_moeda_brasil_correta(resultado_operacional))

                            st.subheader("📊 Detalhamento do Cálculo do EBITDA")
                            nome_coluna_da_filtrado = None
                            for col in df_filtrado.columns:
                                if 'depreciação' in col.lower() and 'amortização' in col.lower():
                                    nome_coluna_da_filtrado = col
                                    break
                            if nome_coluna_da_filtrado and pd.notna(df_filtrado[nome_coluna_da_filtrado].iloc[0]):
                                depreciacao_amortizacao = df_filtrado[nome_coluna_da_filtrado].iloc[0]
                                depreciacao_amortizacao_abs = abs(depreciacao_amortizacao)
                                st.write(f"**Resultado Operacional:** {formatar_moeda_brasil_correta(resultado_operacional)}")
                                st.write(f"**Depreciação e Amortização:** {formatar_moeda_brasil_correta(depreciacao_amortizacao_abs)}")
                                st.write(f"**EBITDA = Resultado Operacional + Depreciação e Amortização**")
                                st.write(f"**EBITDA =** {formatar_moeda_brasil_correta(resultado_operacional)} + {formatar_moeda_brasil_correta(depreciacao_amortizacao_abs)} = **{formatar_moeda_brasil_correta(ebitda_valor)}**")
                            else:
                                st.info("ℹ️ Dados de Depreciação/Amortização não disponíveis. EBITDA calculado como aproximação do Resultado Operacional.")
                                st.write(f"**EBITDA ≈ Resultado Operacional = {formatar_moeda_brasil_correta(ebitda_valor)}**")

                            st.divider()
                            st.subheader("🏦 Valuation por Lucro Econômico/SELIC")
                            col_selic1, col_selic2 = st.columns([2, 1])
                            with col_selic1:
                                st.write("**Configuração da Taxa SELIC:**")
                            with col_selic2:
                                selic_percentual = st.number_input("SELIC (%)", min_value=0.1, max_value=30.0, value=15.0, step=0.1, help="Taxa SELIC atual para cálculo do valuation")

                            lucro_economico_valor = df_filtrado["Lucro Econômico 1"].iloc[0] if "Lucro Econômico 1" in df_filtrado.columns and pd.notna(df_filtrado["Lucro Econômico 1"].iloc[0]) else None
                            if lucro_economico_valor is not None and lucro_economico_valor > 0:
                                valor_empresa = calcular_valuation_lucro_economico_selic(lucro_economico_valor, selic_percentual)
                                if valor_empresa:
                                    valor_empresa_reais = valor_empresa * 1000
                                    numero_acoes = None
                                    if 'Numero_Acoes' in df_filtrado.columns and pd.notna(df_filtrado['Numero_Acoes'].iloc[0]):
                                        numero_acoes = df_filtrado['Numero_Acoes'].iloc[0]
                                    cotacao_esperada = None
                                    if numero_acoes and numero_acoes > 0:
                                        cotacao_esperada = valor_empresa_reais / numero_acoes
                                    dados_cotacao = buscar_cotacao_atual(ticker_selecionado)

                                    col_val1, col_val2, col_val3, col_val4 = st.columns(4)
                                    with col_val1:
                                        st.metric("Valor da Empresa (EV)", formatar_moeda_brasil_correta(valor_empresa_reais / 1000))
                                    with col_val2:
                                        st.metric("Valor da Empresa", formatar_moeda_brasil_correta(valor_empresa_reais / 1000))
                                    with col_val3:
                                        st.metric("Número de Ações", formatar_numero_brasil_correto(numero_acoes, 0) if numero_acoes else "N/A")
                                    with col_val4:
                                        if cotacao_esperada:
                                            st.metric("Cotação Esperada", f"R$ {cotacao_esperada:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                        else:
                                            st.metric("Cotação Esperada*", "N/A")

                                    st.info(f"""
                                    **📊 Fórmula do Valuation (Lucro Econômico/SELIC):**
                                    Valor da Empresa = Lucro Econômico ÷ (SELIC/100)
                                    Valor da Empresa = {formatar_moeda_brasil_correta(lucro_economico_valor)} ÷ ({selic_percentual}%/100)
                                    Valor da Empresa = {formatar_moeda_brasil_correta(valor_empresa)}
                                    Valor da Empresa (R$) = {formatar_moeda_brasil_correta(valor_empresa)} × 1.000 = {formatar_moeda_brasil_correta(valor_empresa_reais / 1000)}
                                    """)

                                    # SELIC implícita
                                    selic_implicita = None
                                    market_cap_atual = None
                                    if dados_cotacao and numero_acoes and numero_acoes > 0:
                                        market_cap_atual = dados_cotacao['cotacao'] * numero_acoes
                                        if lucro_economico_valor > 0:
                                            selic_implicita = (lucro_economico_valor * 1000 / market_cap_atual) * 100
                                            st.info(f"**🎯 SELIC Implícita:** {selic_implicita:.1f}% (Para igualar à cotação atual)")

                                    # EBITDA necessário
                                    ebitda_necessario = None
                                    if dados_cotacao and numero_acoes and numero_acoes > 0:
                                        investimento_medio = df_filtrado["Investimento Médio"].iloc[0] if pd.notna(df_filtrado["Investimento Médio"].iloc[0]) else 0
                                        wacc = df_filtrado["wacc"].iloc[0] if pd.notna(df_filtrado["wacc"].iloc[0]) else 0
                                        nome_coluna_da = None
                                        for col in df_filtrado.columns:
                                            if 'depreciação' in col.lower() and 'amortização' in col.lower():
                                                nome_coluna_da = col
                                                break
                                        depreciacao_amortizacao = 0
                                        if nome_coluna_da and pd.notna(df_filtrado[nome_coluna_da].iloc[0]):
                                            depreciacao_amortizacao = abs(df_filtrado[nome_coluna_da].iloc[0])
                                        ebitda_atual = df_filtrado["EBITDA"].iloc[0] if pd.notna(df_filtrado["EBITDA"].iloc[0]) else 0
                                        if ebitda_atual > 0 and lucro_economico_valor > 0:
                                            relacao_ebitda_lucro_eco = ebitda_atual / lucro_economico_valor
                                        else:
                                            relacao_ebitda_lucro_eco = 2.0
                                        lucro_economico_necessario = market_cap_atual * (selic_percentual / 100) / 1000
                                        ebitda_necessario = lucro_economico_necessario * relacao_ebitda_lucro_eco
                                        if ebitda_necessario > 0:
                                            st.info(f"**📈 EBITDA Necessário:** {formatar_moeda_brasil_correta(ebitda_necessario)}")

                                    if dados_cotacao and cotacao_esperada:
                                        st.divider()
                                        st.subheader("📈 Análise Comparativa com Cotação de Mercado")
                                        col_info1, col_info2, col_info3, col_info4 = st.columns(4)
                                        with col_info1:
                                            st.metric("Cotação Atual", f"R$ {dados_cotacao['cotacao']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                        with col_info2:
                                            diferenca_percentual = ((dados_cotacao['cotacao'] - cotacao_esperada) / cotacao_esperada) * 100
                                            st.metric("Diferença vs Calculado", f"{diferenca_percentual:+.1f}%")
                                        with col_info3:
                                            st.metric("Setor", dados_cotacao['setor'])
                                        with col_info4:
                                            if dados_cotacao['market_cap']:
                                                market_cap_tri = dados_cotacao['market_cap'] / 1e12
                                                st.metric("Market Cap", f"R$ {market_cap_tri:,.2f} tri".replace(",", "X").replace(".", ",").replace("X", "."))
                                        if diferenca_percentual > 20:
                                            st.error("🔴 Sobrevalorizado: cotação atual acima do valuation.")
                                        elif diferenca_percentual < -20:
                                            st.success("🟢 Subvalorizado: cotação atual abaixo do valuation.")
                                        else:
                                            st.info("🟡 Valuation próximo: cotação alinhada com fundamentos.")
                                else:
                                    st.warning("Não foi possível calcular o valuation.")
                            else:
                                st.warning("Dados de Lucro Econômico não disponíveis.")
                        else:
                            st.warning("Dados de EBITDA não disponíveis.")

                # --- ABA 3: ESTRUTURA CAPITAL ---
                with tab3:
                    if is_bank:
                        st.info("ℹ️ Análise de estrutura de capital não se aplica a bancos.")
                    else:
                        st.subheader("Estrutura de Capital")
                        estrutura_cols = ["Percentual Capital Terceiros", "Percentual Capital Próprio"]
                        estrutura_data = []
                        for col in estrutura_cols:
                            if col in df_filtrado.columns:
                                valor = df_filtrado[col].iloc[0]
                                if pd.notna(valor):
                                    estrutura_data.append({"Indicador": col, "Valor": formatar_percentual_brasil(valor, 2), "Status": "✓"})
                                else:
                                    estrutura_data.append({"Indicador": f"{col}*", "Valor": "Não calculado", "Status": "✗"})
                        if estrutura_data:
                            estrutura_df = pd.DataFrame(estrutura_data)
                            st.dataframe(estrutura_df[["Indicador", "Valor"]], use_container_width=True, hide_index=True)
                            valores_validos = [d for d in estrutura_data if d["Status"] == "✓"]
                            if len(valores_validos) >= 2:
                                nomes = ["Capital Terceiros", "Capital Próprio"]
                                valores = [df_filtrado["Percentual Capital Terceiros"].iloc[0], df_filtrado["Percentual Capital Próprio"].iloc[0]]
                                fig_pizza = px.pie(values=valores, names=nomes, title="Composição do Capital")
                                st.plotly_chart(fig_pizza, use_container_width=True)
                        else:
                            st.warning("Não há dados de estrutura de capital disponíveis")

                # --- ABA 4: CUSTO CAPITAL ---
                with tab4:
                    if is_bank:
                        st.info("ℹ️ Análise de custo de capital não se aplica a bancos.")
                    else:
                        st.subheader("Custo de Capital")
                        custo_cols = ["ki", "ke", "wacc"]
                        custo_data = []
                        for col in custo_cols:
                            if col in df_filtrado.columns:
                                valor = df_filtrado[col].iloc[0]
                                if pd.notna(valor):
                                    custo_data.append({"Indicador": col, "Valor": formatar_percentual_brasil(valor, 2), "Status": "✓"})
                                else:
                                    custo_data.append({"Indicador": f"{col}*", "Valor": "Não calculado", "Status": "✗"})
                        if custo_data:
                            custo_df = pd.DataFrame(custo_data)
                            st.dataframe(custo_df[["Indicador", "Valor"]], use_container_width=True, hide_index=True)
                        else:
                            st.warning("Não há dados de custo de capital disponíveis")

                # --- ABA 5: LUCRO ECONÔMICO ---
                with tab5:
                    if is_bank:
                        st.info("ℹ️ Lucro Econômico não se aplica a bancos.")
                    else:
                        st.subheader("Lucro Econômico")
                        lucro_cols = ["Lucro Econômico 1", "Lucro Econômico 2"]
                        lucro_data = []
                        for col in lucro_cols:
                            if col in df_filtrado.columns:
                                valor = df_filtrado[col].iloc[0]
                                if pd.notna(valor):
                                    lucro_data.append({"Indicador": col, "Valor": formatar_moeda_brasil_correta(valor), "Status": "✓"})
                                else:
                                    lucro_data.append({"Indicador": f"{col}*", "Valor": "Não calculado", "Status": "✗"})
                        if lucro_data:
                            lucro_df = pd.DataFrame(lucro_data)
                            st.dataframe(lucro_df[["Indicador", "Valor"]], use_container_width=True, hide_index=True)
                        else:
                            st.warning("Não há dados de lucro econômico disponíveis")

                # --- ABA 6: FLUXO DE CAIXA ---
                with tab6:
                    st.subheader("💵 Fluxo de Caixa Operacional")
                    if 'Caixa Líquido Atividades Operacionais' in df_filtrado.columns:
                        valor_caixa = df_filtrado['Caixa Líquido Atividades Operacionais'].iloc[0]
                        if pd.notna(valor_caixa):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Caixa Operacional", formatar_moeda_brasil_correta(valor_caixa))
                            with col2:
                                lucro_liquido = df_filtrado["Lucro/Prejuízo Consolidado do Período"].iloc[0] if pd.notna(df_filtrado["Lucro/Prejuízo Consolidado do Período"].iloc[0]) else 0
                                if lucro_liquido != 0:
                                    relacao_caixa_lucro = (valor_caixa / lucro_liquido) * 100
                                    st.metric("Caixa/Lucro", f"{relacao_caixa_lucro:.1f}%")
                            with col3:
                                if not is_bank:
                                    ebitda = df_filtrado["EBITDA"].iloc[0] if "EBITDA" in df_filtrado.columns and pd.notna(df_filtrado["EBITDA"].iloc[0]) else 0
                                    if ebitda != 0:
                                        relacao_caixa_ebitda = (valor_caixa / ebitda) * 100
                                        st.metric("Caixa/EBITDA", f"{relacao_caixa_ebitda:.1f}%")
                                else:
                                    st.metric("Caixa/EBITDA", "N/A (Banco)")
                            st.subheader("📊 Análise do Fluxo de Caixa")
                            if valor_caixa > 0:
                                st.success("**✅ Geração Positiva de Caixa**")
                            else:
                                st.warning("**⚠️ Geração Negativa de Caixa**")
                        else:
                            st.warning("Dados de Caixa Líquido de Atividades Operacionais não disponíveis para este ano")
                    else:
                        st.warning("Coluna 'Caixa Líquido Atividades Operacionais' não encontrada no dataset")

                # --- ABA 7: DADOS BRUTOS ---
                with tab7:
                    st.subheader("Dados Financeiros Brutos")
                    dados_brutos_cols = [
                        "Receita de Venda de Bens e/ou Serviços",
                        "Resultado Bruto",
                        "Resultado Antes do Resultado Financeiro e dos Tributos",
                        "Lucro/Prejuízo Consolidado do Período",
                        "Despesas Financeiras",
                        "Pagamento de Dividendos",
                        "Ativo Total",
                        "Patrimônio Líquido Consolidado",
                        "Empréstimos e Financiamentos - Circulante",
                        "Empréstimos e Financiamentos - Não Circulante",
                        "Caixa Líquido Atividades Operacionais"
                    ]
                    if is_bank:
                        dados_brutos_cols.append("Resultado Abrangente do Período")
                    nome_coluna_da_brutos = None
                    for col in df_filtrado.columns:
                        if 'depreciação' in col.lower() and 'amortização' in col.lower():
                            nome_coluna_da_brutos = col
                            break
                    if nome_coluna_da_brutos:
                        dados_brutos_cols.append(nome_coluna_da_brutos)
                    dados_brutos = {}
                    for col in dados_brutos_cols:
                        if col in df_filtrado.columns:
                            valor = df_filtrado[col].iloc[0]
                            dados_brutos[col] = formatar_moeda_brasil_correta(valor) if pd.notna(valor) else "N/A"
                    st.dataframe(pd.DataFrame.from_dict(dados_brutos, orient='index', columns=['Valor']), use_container_width=True)

            else:
                st.warning(f"Não há dados disponíveis para {ticker_selecionado} no ano {ano_selecionado}")

        # ---- EVOLUÇÃO TEMPORAL (Visão por Empresa) ----
        with tab_evolucao:
            st.subheader(f"Evolução Temporal - {ticker_selecionado}")
            if len(df_empresa_todos_anos) > 1:
                is_bank_series = df_empresa_todos_anos['is_bank'].iloc[0] if 'is_bank' in df_empresa_todos_anos.columns else False

                col1, col2 = st.columns(2)
                with col1:
                    fig_rentabilidade = go.Figure()
                    if is_bank_series:
                        indicadores_rentabilidade = ['ROE', 'ROA']
                    else:
                        indicadores_rentabilidade = ['ROE', 'ROA', 'ROI', 'Margem Líquida']
                    cores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
                    for i, indicador in enumerate(indicadores_rentabilidade):
                        if indicador in df_empresa_todos_anos.columns:
                            dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
                            if not dados_validos.empty:
                                fig_rentabilidade.add_trace(go.Scatter(
                                    x=dados_validos['Ano'], y=dados_validos[indicador],
                                    mode='lines+markers', name=indicador,
                                    line=dict(color=cores[i % len(cores)], width=3), marker=dict(size=8)
                                ))
                    fig_rentabilidade.update_layout(title='Evolução da Rentabilidade', xaxis_title='Ano', yaxis_title='Percentual', yaxis_tickformat=',.2%', height=400, showlegend=True)
                    st.plotly_chart(fig_rentabilidade, use_container_width=True)

                with col2:
                    if not is_bank_series:
                        fig_estrutura = go.Figure()
                        indicadores_estrutura = ['Percentual Capital Terceiros', 'Percentual Capital Próprio']
                        cores_estrutura = ['#e74c3c', '#2ecc71']
                        for i, indicador in enumerate(indicadores_estrutura):
                            if indicador in df_empresa_todos_anos.columns:
                                dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
                                if not dados_validos.empty:
                                    fig_estrutura.add_trace(go.Scatter(
                                        x=dados_validos['Ano'], y=dados_validos[indicador],
                                        mode='lines+markers', name=indicador,
                                        line=dict(color=cores_estrutura[i % len(cores_estrutura)], width=3),
                                        marker=dict(size=8), stackgroup='one' if i == 0 else None
                                    ))
                        fig_estrutura.update_layout(title='Evolução da Estrutura de Capital', xaxis_title='Ano', yaxis_title='Percentual', yaxis_tickformat=',.2%', height=400, showlegend=True)
                        st.plotly_chart(fig_estrutura, use_container_width=True)
                    else:
                        if 'PL Médio' in df_empresa_todos_anos.columns:
                            fig_pl = px.line(df_empresa_todos_anos, x='Ano', y='PL Médio', title='Evolução do Patrimônio Líquido Médio')
                            fig_pl.update_layout(yaxis_tickformat=',.0f')
                            st.plotly_chart(fig_pl, use_container_width=True)

                if not is_bank_series:
                    col3, col4 = st.columns(2)
                    with col3:
                        fig_custo = go.Figure()
                        indicadores_custo = ['ki', 'ke', 'wacc']
                        nomes_custo = ['Custo da Dívida (ki)', 'Custo do Capital Próprio (ke)', 'WACC']
                        cores_custo = ['#9b59b6', '#3498db', '#f39c12']
                        for i, indicador in enumerate(indicadores_custo):
                            if indicador in df_empresa_todos_anos.columns:
                                dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
                                if not dados_validos.empty:
                                    fig_custo.add_trace(go.Scatter(
                                        x=dados_validos['Ano'], y=dados_validos[indicador],
                                        mode='lines+markers', name=nomes_custo[i],
                                        line=dict(color=cores_custo[i % len(cores_custo)], width=3), marker=dict(size=8)
                                    ))
                        fig_custo.update_layout(title='Evolução do Custo de Capital', xaxis_title='Ano', yaxis_title='Percentual', yaxis_tickformat=',.2%', height=400, showlegend=True)
                        st.plotly_chart(fig_custo, use_container_width=True)
                    with col4:
                        fig_margens = go.Figure()
                        indicadores_margens = ['Margem Bruta', 'Margem Operacional', 'Margem Líquida']
                        cores_margens = ['#16a085', '#27ae60', '#2980b9']
                        for i, indicador in enumerate(indicadores_margens):
                            if indicador in df_empresa_todos_anos.columns:
                                dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
                                if not dados_validos.empty:
                                    fig_margens.add_trace(go.Scatter(
                                        x=dados_validos['Ano'], y=dados_validos[indicador],
                                        mode='lines+markers', name=indicador,
                                        line=dict(color=cores_margens[i % len(cores_margens)], width=3), marker=dict(size=8)
                                    ))
                        fig_margens.update_layout(title='Evolução das Margens', xaxis_title='Ano', yaxis_title='Percentual', yaxis_tickformat=',.2%', height=400, showlegend=True)
                        st.plotly_chart(fig_margens, use_container_width=True)

                if not is_bank_series:
                    st.subheader("💰 Evolução do Lucro Econômico e EBITDA")
                    col5, col6 = st.columns(2)
                    with col5:
                        fig_lucro_absoluto = go.Figure()
                        indicadores_lucro = ['Lucro Econômico 1', 'Lucro Econômico 2']
                        nomes_lucro = ['Lucro Econômico 1', 'Lucro Econômico 2']
                        cores_lucro = ['#e74c3c', '#3498db']
                        for i, indicador in enumerate(indicadores_lucro):
                            if indicador in df_empresa_todos_anos.columns:
                                dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
                                if not dados_validos.empty:
                                    fig_lucro_absoluto.add_trace(go.Scatter(
                                        x=dados_validos['Ano'], y=dados_validos[indicador],
                                        mode='lines+markers', name=nomes_lucro[i],
                                        line=dict(color=cores_lucro[i % len(cores_lucro)], width=3), marker=dict(size=8)
                                    ))
                        fig_lucro_absoluto.update_layout(title='Lucro Econômico (Valores Absolutos)', xaxis_title='Ano', yaxis_title='Valor', yaxis_tickformat=',.0f', height=400, showlegend=True)
                        st.plotly_chart(fig_lucro_absoluto, use_container_width=True)
                    with col6:
                        fig_ebitda = go.Figure()
                        indicadores_ebitda = ['EBITDA', 'Resultado Antes do Resultado Financeiro e dos Tributos']
                        nomes_ebitda = ['EBITDA', 'Resultado Operacional']
                        cores_ebitda = ['#2ecc71', '#34495e']
                        for i, indicador in enumerate(indicadores_ebitda):
                            if indicador in df_empresa_todos_anos.columns:
                                dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
                                if not dados_validos.empty:
                                    fig_ebitda.add_trace(go.Scatter(
                                        x=dados_validos['Ano'], y=dados_validos[indicador],
                                        mode='lines+markers', name=nomes_ebitda[i],
                                        line=dict(color=cores_ebitda[i % len(cores_ebitda)], width=3), marker=dict(size=8)
                                    ))
                        fig_ebitda.update_layout(title='EBITDA vs Resultado Operacional', xaxis_title='Ano', yaxis_title='Valor', yaxis_tickformat=',.0f', height=400, showlegend=True)
                        st.plotly_chart(fig_ebitda, use_container_width=True)

                # Fluxo de caixa (todos)
                st.subheader("💸 Evolução do Fluxo de Caixa Operacional")
                if 'Caixa Líquido Atividades Operacionais' in df_empresa_todos_anos.columns:
                    col7, col8 = st.columns(2)
                    with col7:
                        fig_caixa = px.line(df_empresa_todos_anos, x='Ano', y='Caixa Líquido Atividades Operacionais', title='Caixa Líquido de Atividades Operacionais')
                        fig_caixa.update_layout(yaxis_title='Caixa Operacional', yaxis_tickformat=',.0f', height=400)
                        st.plotly_chart(fig_caixa, use_container_width=True)
                    with col8:
                        df_comparacao = df_empresa_todos_anos.copy()
                        df_comparacao = df_comparacao[df_comparacao['Caixa Líquido Atividades Operacionais'].notna() & df_comparacao['Lucro/Prejuízo Consolidado do Período'].notna()]
                        if not df_comparacao.empty:
                            fig_comparacao = go.Figure()
                            fig_comparacao.add_trace(go.Scatter(
                                x=df_comparacao['Ano'], y=df_comparacao['Caixa Líquido Atividades Operacionais'],
                                mode='lines+markers', name='Caixa Operacional',
                                line=dict(color='#27ae60', width=3), marker=dict(size=8)
                            ))
                            fig_comparacao.add_trace(go.Scatter(
                                x=df_comparacao['Ano'], y=df_comparacao['Lucro/Prejuízo Consolidado do Período'],
                                mode='lines+markers', name='Lucro Líquido',
                                line=dict(color='#e74c3c', width=3), marker=dict(size=8)
                            ))
                            fig_comparacao.update_layout(title='Comparação: Caixa Operacional vs Lucro Líquido', xaxis_title='Ano', yaxis_title='Valor', yaxis_tickformat=',.0f', height=400, showlegend=True)
                            st.plotly_chart(fig_comparacao, use_container_width=True)

                st.subheader("📋 Resumo da Evolução - Principais Indicadores")
                if is_bank_series:
                    indicadores_resumo = ['ROE', 'ROA', 'Margem Bruta', 'Margem Operacional', 'Resultado Abrangente do Período', 'PL Médio', 'Caixa Líquido Atividades Operacionais']
                else:
                    indicadores_resumo = ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio', 'Lucro Econômico 1', 'Resultado Antes do Resultado Financeiro e dos Tributos', 'EBITDA', 'Caixa Líquido Atividades Operacionais']
                df_resumo = df_empresa_todos_anos[['Ano'] + [col for col in indicadores_resumo if col in df_empresa_todos_anos.columns]]
                def formatar_valor(valor, coluna):
                    if coluna in ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio', 'Margem Bruta', 'Margem Operacional']:
                        return formatar_percentual_brasil(valor, 2) if pd.notna(valor) else "N/A"
                    elif coluna in ['Lucro Econômico 1', 'Resultado Antes do Resultado Financeiro e dos Tributos', 'EBITDA', 'Caixa Líquido Atividades Operacionais', 'PL Médio', 'Resultado Abrangente do Período']:
                        return formatar_moeda_brasil_correta(valor) if pd.notna(valor) else "N/A"
                    else:
                        return valor
                df_resumo_formatado = df_resumo.copy()
                for col in df_resumo_formatado.columns:
                    if col != 'Ano':
                        df_resumo_formatado[col] = df_resumo_formatado[col].apply(lambda x: formatar_valor(x, col))
                st.dataframe(df_resumo_formatado, use_container_width=True)
            else:
                st.info("ℹ️ São necessários dados de múltiplos anos para análise de evolução temporal")
    else:
        st.warning("Empresa não encontrada na base de dados.")

# ==============================
# MODO: ANÁLISE SETORIAL
# ==============================
elif modo_analise == "🏭 Análise Setorial":
    st.header(f"🏭 Análise Setorial - {setor_selecionado}")
    if not df_setor_todos_anos.empty:
        tab_atual_setor, tab_evolucao_setor = st.tabs(["📊 Análise do Ano", "📈 Evolução Temporal"])
        with tab_atual_setor:
            st.subheader(f"Ano {ano_selecionado}")
            if not df_filtrado.empty:
                is_bank_setor = setor_selecionado.lower() in ['bancos', 'instituição financeira', 'financeiro']
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Empresas no Setor", df_filtrado["Ticker"].nunique())
                with col2:
                    receita_setor = df_filtrado["Receita de Venda de Bens e/ou Serviços"].sum()
                    st.metric("Receita Total", formatar_moeda_brasil_correta(receita_setor, 2))
                with col3:
                    lucro_setor = df_filtrado["Lucro/Prejuízo Consolidado do Período"].sum()
                    st.metric("Lucro Total", formatar_moeda_brasil_correta(lucro_setor, 2))
                with col4:
                    pl_setor = df_filtrado["Patrimônio Líquido Consolidado"].sum()
                    st.metric("Patrimônio Líquido", formatar_moeda_brasil_correta(pl_setor, 2))
                st.divider()

                st.subheader("Top 10 Empresas do Setor por ROE")
                top_roe_setor = df_filtrado[df_filtrado["ROE"].notna()].nlargest(10, "ROE")[["Ticker", "ROE"]]
                if not top_roe_setor.empty:
                    fig_roe = px.bar(top_roe_setor, x="Ticker", y="ROE", title="ROE por Empresa no Setor")
                    fig_roe.update_layout(yaxis_tickformat=',.2%')
                    st.plotly_chart(fig_roe, use_container_width=True)
                else:
                    st.warning("Não há dados de ROE disponíveis para este setor")

                if not is_bank_setor:
                    st.subheader("Estrutura de Capital no Setor")
                    estrutura_setor = df_filtrado[df_filtrado["Percentual Capital Próprio"].notna()].nlargest(15, "Patrimônio Líquido Consolidado")
                    if not estrutura_setor.empty:
                        fig_estrutura = px.bar(estrutura_setor, x="Ticker", y=["Percentual Capital Terceiros", "Percentual Capital Próprio"],
                                               title="Estrutura de Capital das Principais Empresas do Setor", barmode='stack')
                        fig_estrutura.update_layout(yaxis_tickformat=',.2%')
                        st.plotly_chart(fig_estrutura, use_container_width=True)
                    else:
                        st.warning("Não há dados de estrutura de capital disponíveis para este setor")
                else:
                    st.info("ℹ️ Análise de estrutura de capital não se aplica a bancos.")

                st.subheader("Ranking de Rentabilidade no Setor")
                if is_bank_setor:
                    rentabilidade_setor = df_filtrado[df_filtrado["ROE"].notna() & df_filtrado["ROA"].notna()].nlargest(15, "ROE")[["Ticker", "ROE", "ROA"]]
                else:
                    rentabilidade_setor = df_filtrado[df_filtrado["ROE"].notna() & df_filtrado["ROA"].notna() & df_filtrado["ROI"].notna()].nlargest(15, "ROE")[["Ticker", "ROE", "ROA", "ROI", "Margem Líquida"]]
                if not rentabilidade_setor.empty:
                    if is_bank_setor:
                        rentabilidade_formatado = formatar_dataframe_percentual(rentabilidade_setor, ['ROE', 'ROA'])
                    else:
                        rentabilidade_formatado = formatar_dataframe_percentual(rentabilidade_setor, ['ROE', 'ROA', 'ROI', 'Margem Líquida'])
                    st.dataframe(rentabilidade_formatado, use_container_width=True)
                else:
                    st.warning("Não há dados de rentabilidade suficientes para exibir o ranking")
            else:
                st.warning(f"Não há dados disponíveis para o setor {setor_selecionado} no ano {ano_selecionado}")

        with tab_evolucao_setor:
            st.subheader(f"Evolução Temporal do Setor - {setor_selecionado}")
            if len(df_setor_todos_anos['Ano'].unique()) > 1:
                is_bank_setor = setor_selecionado.lower() in ['bancos', 'instituição financeira', 'financeiro']
                if is_bank_setor:
                    indicadores_setor = ['ROE', 'ROA', 'Margem Bruta', 'Margem Operacional', 'Resultado Abrangente do Período', 'PL Médio']
                else:
                    indicadores_setor = ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio', 'Lucro Econômico 1', 'EBITDA']
                df_setor_evolucao = df_setor_todos_anos.groupby('Ano')[indicadores_setor].median().reset_index()

                col1, col2 = st.columns(2)
                with col1:
                    fig_setor_rent = go.Figure()
                    if is_bank_setor:
                        indicadores_rent_setor = ['ROE', 'ROA']
                    else:
                        indicadores_rent_setor = ['ROE', 'ROA', 'ROI']
                    cores_setor = ['#1f77b4', '#ff7f0e', '#2ca02c']
                    for i, indicador in enumerate(indicadores_rent_setor):
                        if indicador in df_setor_evolucao.columns:
                            dados_validos = df_setor_evolucao[df_setor_evolucao[indicador].notna()]
                            if not dados_validos.empty:
                                fig_setor_rent.add_trace(go.Scatter(
                                    x=dados_validos['Ano'], y=dados_validos[indicador],
                                    mode='lines+markers', name=indicador,
                                    line=dict(color=cores_setor[i % len(cores_setor)], width=3), marker=dict(size=8)
                                ))
                    fig_setor_rent.update_layout(title='Evolução da Rentabilidade do Setor (Mediana)', xaxis_title='Ano', yaxis_title='Percentual', yaxis_tickformat=',.2%', height=400, showlegend=True)
                    st.plotly_chart(fig_setor_rent, use_container_width=True)

                with col2:
                    if not is_bank_setor:
                        fig_setor_estrutura = go.Figure()
                        indicadores_estrutura_setor = ['Percentual Capital Próprio', 'wacc']
                        nomes_estrutura = ['Capital Próprio (%)', 'WACC']
                        cores_estrutura_setor = ['#2ecc71', '#f39c12']
                        for i, indicador in enumerate(indicadores_estrutura_setor):
                            if indicador in df_setor_evolucao.columns:
                                dados_validos = df_setor_evolucao[df_setor_evolucao[indicador].notna()]
                                if not dados_validos.empty:
                                    fig_setor_estrutura.add_trace(go.Scatter(
                                        x=dados_validos['Ano'], y=dados_validos[indicador],
                                        mode='lines+markers', name=nomes_estrutura[i],
                                        line=dict(color=cores_estrutura_setor[i % len(cores_estrutura_setor)], width=3), marker=dict(size=8)
                                    ))
                        fig_setor_estrutura.update_layout(title='Evolução da Estrutura e Custo de Capital (Mediana)', xaxis_title='Ano', yaxis_title='Percentual', yaxis_tickformat=',.2%', height=400, showlegend=True)
                        st.plotly_chart(fig_setor_estrutura, use_container_width=True)
                    else:
                        if 'PL Médio' in df_setor_evolucao.columns:
                            fig_pl_setor = px.line(df_setor_evolucao, x='Ano', y='PL Médio', title='Evolução do PL Médio (Mediana)')
                            fig_pl_setor.update_layout(yaxis_tickformat=',.0f')
                            st.plotly_chart(fig_pl_setor, use_container_width=True)

                if not is_bank_setor:
                    st.subheader("💰 Evolução do Lucro Econômico e EBITDA no Setor")
                    col3, col4 = st.columns(2)
                    with col3:
                        if 'Lucro Econômico 1' in df_setor_evolucao.columns:
                            fig_setor_lucro = px.line(df_setor_evolucao, x='Ano', y='Lucro Econômico 1', title='Lucro Econômico Médio do Setor (Mediana)')
                            fig_setor_lucro.update_layout(yaxis_title='Lucro Econômico', yaxis_tickformat=',.0f', height=400)
                            st.plotly_chart(fig_setor_lucro, use_container_width=True)
                    with col4:
                        if 'EBITDA' in df_setor_evolucao.columns:
                            fig_setor_ebitda = px.line(df_setor_evolucao, x='Ano', y='EBITDA', title='EBITDA Médio do Setor (Mediana)')
                            fig_setor_ebitda.update_layout(yaxis_title='EBITDA', yaxis_tickformat=',.0f', height=400)
                            st.plotly_chart(fig_setor_ebitda, use_container_width=True)

                st.subheader("📋 Resumo da Evolução do Setor - Principais Indicadores")
                def formatar_valor_setor(valor, coluna):
                    if coluna in ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio', 'Margem Bruta', 'Margem Operacional']:
                        return formatar_percentual_brasil(valor, 2) if pd.notna(valor) else "N/A"
                    elif coluna in ['Lucro Econômico 1', 'EBITDA', 'PL Médio', 'Resultado Abrangente do Período']:
                        return formatar_moeda_brasil_correta(valor) if pd.notna(valor) else "N/A"
                    else:
                        return valor
                df_setor_formatado = df_setor_evolucao.copy()
                for col in df_setor_formatado.columns:
                    if col != 'Ano':
                        df_setor_formatado[col] = df_setor_formatado[col].apply(lambda x: formatar_valor_setor(x, col))
                st.dataframe(df_setor_formatado, use_container_width=True)

                st.subheader("📊 Dispersão de Rentabilidade no Setor")
                if ano_selecionado in df_setor_todos_anos['Ano'].values:
                    df_setor_ano = df_setor_todos_anos[df_setor_todos_anos['Ano'] == ano_selecionado]
                    if not df_setor_ano.empty and 'ROE' in df_setor_ano.columns:
                        fig_dispersao = px.box(df_setor_ano, y='ROE', title=f'Distribuição do ROE no Setor - {ano_selecionado}')
                        fig_dispersao.update_layout(yaxis_tickformat=',.2%')
                        st.plotly_chart(fig_dispersao, use_container_width=True)
            else:
                st.info("ℹ️ São necessários dados de múltiplos anos para análise de evolução temporal do setor")

# ==============================
# SEÇÃO DE FÓRMULAS DOS INDICADORES
# ==============================
st.divider()
st.header("📚 Fórmulas dos Indicadores (VELLANI, 2024)")

formulas = {
    "ROE (Return on Equity)": "Lucro Líquido ÷ Patrimônio Líquido Médio",
    "ROA (Return on Assets)": "Resultado Operacional ÷ Ativo Total Médio",
    "ROI (Return on Investment)": "Resultado Operacional ÷ Investimento Médio (NÃO se aplica a Bancos)",
    "Investimento Médio": "Média[(Empréstimos Circulante + Empréstimos Não Circulante + PL) atual e anterior]",
    "Margem Bruta": "Resultado Bruto ÷ Receita de Vendas",
    "Margem Operacional": "Resultado Operacional ÷ Receita de Vendas",
    "Margem Líquida": "Lucro Líquido ÷ Receita de Vendas (NÃO se aplica a Bancos)",
    "ki (Custo da Dívida)": "Despesas Financeiras ÷ Passivo Oneroso Médio (NÃO se aplica a Bancos)",
    "ke (Custo do Capital Próprio)": "Dividendos Pagos ÷ Patrimônio Líquido Médio (NÃO se aplica a Bancos)",
    "WACC": "(ki × % Capital Terceiros) + (ke × % Capital Próprio) (NÃO se aplica a Bancos)",
    "Lucro Econômico 1": "(ROI - WACC) × Investimento Médio (NÃO se aplica a Bancos)",
    "Lucro Econômico 2": "Resultado Operacional - (WACC × Investimento Médio) (NÃO se aplica a Bancos)",
    "EBITDA": "Resultado Operacional + Depreciação + Amortização (NÃO se aplica a Bancos)",
    "Valuation Lucro Econômico/SELIC": "Lucro Econômico ÷ (SELIC/100) (NÃO se aplica a Bancos)",
    "Valuation para Bancos": "(LPA - (VPA × r)) / r, onde LPA = Lucro Abrangente / Ações, VPA = PL Médio / Ações, r = taxa de desconto",
    "Percentual Capital Terceiros": "(Passivo Circulante + Não Circulante) ÷ Total Passivo (NÃO se aplica a Bancos)",
    "Percentual Capital Próprio": "Patrimônio Líquido ÷ Total Passivo (NÃO se aplica a Bancos)",
    "Caixa Líquido Atividades Operacionais": "Fluxo de caixa gerado/consumido pelas atividades operacionais"
}

col1, col2 = st.columns(2)
with col1:
    for i, (indicador, formula) in enumerate(formulas.items()):
        if i < len(formulas) // 2:
            with st.expander(f"**{indicador}**"):
                st.write(f"`{formula}`")
with col2:
    for i, (indicador, formula) in enumerate(formulas.items()):
        if i >= len(formulas) // 2:
            with st.expander(f"**{indicador}**"):
                st.write(f"`{formula}`")

# ==============================
# INFORMAÇÕES GERAIS
# ==============================
st.sidebar.divider()
st.sidebar.header("ℹ️ Informações")
st.sidebar.info(
    "Este dashboard apresenta os principais indicadores financeiros "
    "calculados conforme Vellani (2024) - com suporte a análise de Bancos."
)

st.divider()
st.caption(f"📊 Dashboard CVM - Indicadores Financeiros | Dados atualizados para {ano_selecionado} | Total de empresas na base: {df['Ticker'].nunique()}")

with st.sidebar.expander("💡 Livro referência: Análise das Demonstrações Financeiras. Editora Viena. 2024. Autor Cássio Luiz Vellani."):
    st.write("""
    **Cálculos Verificados:**
    - Lucro Econômico 1 = Lucro Econômico 2 (para não bancos)
    - Consistência garantida pela fórmula do ROI.
    - EBITDA corrigido usando exclusivamente a coluna 'Depreciação e amortização'.
    - Valuation para bancos conforme fórmula do livro (p. 180).
    - Suporte a busca de cotação via Yahoo Finance.
    """)
