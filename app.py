
**💡 Interpretação:**
- Para justificar a **cotação atual** (R$ {dados_cotacao['cotacao']:,.2f}) com **SELIC atual** ({selic_percentual}%)
- A empresa precisaria ter um **EBITDA** de **{formatar_moeda_brasil_correta(ebitda_necessario)}**
- EBITDA Atual: {formatar_moeda_brasil_correta(ebitda_atual)}
- Variação necessária: {variacao_necessaria:+.1f}%
""")

# Análise do EBITDA necessário
if variacao_necessaria > 0:
    st.warning(f"**📈 EBITDA precisa crescer {variacao_necessaria:+.1f}%**")
    st.write("Para justificar a cotação atual, a empresa precisa **aumentar** seu EBITDA significativamente.")
else:
    st.success(f"**✅ EBITDA atual já justifica a cotação**")
    st.write("O EBITDA atual já é suficiente para justificar a cotação de mercado com a SELIC atual.")

# Mostrar também os dados de EBITDA para referência
if ebitda_valor:
st.info(f"""
**📊 Dados de Referência Atuais:**
- **EBITDA:** {formatar_moeda_brasil_correta(ebitda_valor)}
- **Lucro Econômico:** {formatar_moeda_brasil_correta(lucro_economico_valor)}
- **Investimento Médio:** {formatar_moeda_brasil_correta(df_filtrado['Investimento Médio'].iloc[0])}
- **ROI:** {formatar_percentual_brasil(df_filtrado['ROI'].iloc[0], 2)}
- **WACC:** {formatar_percentual_brasil(df_filtrado['wacc'].iloc[0], 2)}
""")

# Se temos dados da cotação, fazer análise comparativa
if dados_cotacao:
st.divider()
st.subheader("📈 Análise Comparativa com Cotação de Mercado")

# Informações da empresa
col_info1, col_info2, col_info3, col_info4 = st.columns(4)

with col_info1:
    st.metric("Cotação Atual", f"R$ {dados_cotacao['cotacao']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

with col_info2:
    if cotacao_esperada:
        diferenca_percentual = ((dados_cotacao['cotacao'] - cotacao_esperada) / cotacao_esperada) * 100
        st.metric(
            "Diferença vs Calculado", 
            f"{diferenca_percentual:+.1f}%",
            delta=f"{diferenca_percentual:+.1f}%"
        )

with col_info3:
    st.metric("Setor", dados_cotacao['setor'])

with col_info4:
    if dados_cotacao['market_cap']:
        market_cap_tri = dados_cotacao['market_cap'] / 1e12
        st.metric("Market Cap", f"R$ {market_cap_tri:,.2f} tri".replace(",", "X").replace(".", ",").replace("X", "."))

# Análise de valuation implícito
st.write("**💡 Interpretação:**")

if cotacao_esperada:
    st.write(f"""
    - **Lucro Econômico Anual:** {formatar_moeda_brasil_correta(lucro_economico_valor)}
    - **Taxa de Desconto (SELIC):** {selic_percentual}% a.a.
    - **Valor Justo Calculado:** {formatar_moeda_brasil_correta(valor_empresa_reais / 1000)}
    - **Número de Ações:** {formatar_numero_brasil_correto(numero_acoes, 0)}
    - **Cotação Esperada:** R$ {cotacao_esperada:,.2f}
    - **Cotação Atual ({dados_cotacao['data_atualizacao']}):** R$ {dados_cotacao['cotacao']:,.2f}
    - **Diferença:** {diferenca_percentual:+.1f}%
    """)
else:
    st.write(f"""
    - **Lucro Econômico Anual:** {formatar_moeda_brasil_correta(lucro_economico_valor)}
    - **Taxa de Desconto (SELIC):** {selic_percentual}% a.a.
    - **Valor Justo Calculado:** {formatar_moeda_brasil_correta(valor_empresa_reais / 1000)}
    - **Cotação Atual ({dados_cotacao['data_atualizacao']}):** R$ {dados_cotacao['cotacao']:,.2f}
    """)

# Gráfico comparativo
if cotacao_esperada:
    st.subheader("🎯 Comparação Visual")
    
    fig_comparativo = criar_grafico_comparativo(
        cotacao_esperada, 
        dados_cotacao['cotacao'], 
        ticker_selecionado
    )
    st.plotly_chart(fig_comparativo, use_container_width=True)
    
    # Análise qualitativa
    if diferenca_percentual > 20:
        st.error("""
        **🔴 Sobrevalorizado:** A cotação atual está significativamente acima do valuation calculado.
        *Possíveis razões:* Expectativas de crescimento futuro, fatores setoriais favoráveis, ou especulação de mercado.
        """)
    elif diferenca_percentual < -20:
        st.success("""
        **🟢 Subvalorizado:** A cotação atual está significativamente abaixo do valuation calculado.
        *Possíveis oportunidades:* Valorização potencial, retorno ao valuation justo.
        """)
    else:
        st.info("""
        **🟡 Valuation Próximo:** A cotação atual está alinhada com o valuation calculado.
        *Interpretação:* Preço de mercado condizente com fundamentos.
        """)

else:
st.warning("""
**ℹ️ Informações Adicionais Necessárias:**
- Para análise completa, é necessário o número de ações em circulação
- Com o número de ações, podemos calcular o preço por ação teórico
- Considere também: crescimento futuro, perspectivas do setor, concorrência
""")

else:
st.warning("Não foi possível calcular o valuation. Lucro Econômico inválido ou negativo.")
else:
st.warning("Dados de Lucro Econômico não disponíveis para cálculo do valuation.")

else:
st.warning("Dados de EBITDA não disponíveis")

# Aba Estrutura de Capital (apenas não bancos)
if not is_bank and 'tab3' in locals():
with tab3:
st.subheader("Estrutura de Capital")
estrutura_cols = ["Percentual Capital Terceiros", "Percentual Capital Próprio"]
estrutura_data = []

for col in estrutura_cols:
if col in df_filtrado.columns:
valor = df_filtrado[col].iloc[0]
if pd.notna(valor):
estrutura_data.append({
"Indicador": col,
"Valor": formatar_percentual_brasil(valor, 2),
"Status": "✓"
})
else:
estrutura_data.append({
"Indicador": f"{col}*",
"Valor": "Não calculado",
"Status": "✗"
})

if estrutura_data:
estrutura_df = pd.DataFrame(estrutura_data)
st.dataframe(estrutura_df[["Indicador", "Valor"]], use_container_width=True, hide_index=True)

# Gráfico de pizza da estrutura de capital (apenas se ambos os valores estiverem disponíveis)
valores_validos = [d for d in estrutura_data if d["Status"] == "✓"]
if len(valores_validos) >= 2:
nomes = ["Capital Terceiros", "Capital Próprio"]
valores = [df_filtrado["Percentual Capital Terceiros"].iloc[0], 
  df_filtrado["Percentual Capital Próprio"].iloc[0]]

fig_pizza = px.pie(
values=valores,
names=nomes,
title="Composição do Capital"
)
st.plotly_chart(fig_pizza, use_container_width=True)
else:
st.warning("Não há dados de estrutura de capital disponíveis")

# Aba Custo de Capital (apenas não bancos)
if not is_bank and 'tab4' in locals():
with tab4:
st.subheader("Custo de Capital")
custo_cols = ["ki", "ke", "wacc"]
custo_data = []

for col in custo_cols:
if col in df_filtrado.columns:
valor = df_filtrado[col].iloc[0]
if pd.notna(valor):
custo_data.append({
"Indicador": col,
"Valor": formatar_percentual_brasil(valor, 2),
"Status": "✓"
})
else:
custo_data.append({
"Indicador": f"{col}*",
"Valor": "Não calculado",
"Status": "✗"
})

if custo_data:
custo_df = pd.DataFrame(custo_data)
st.dataframe(custo_df[["Indicador", "Valor"]], use_container_width=True, hide_index=True)
else:
st.warning("Não há dados de custo de capital disponíveis")

# Aba Lucro Econômico (apenas não bancos)
if not is_bank and 'tab5' in locals():
with tab5:
st.subheader("Lucro Econômico")
lucro_cols = ["Lucro Econômico 1", "Lucro Econômico 2"]
lucro_data = []

for col in lucro_cols:
if col in df_filtrado.columns:
valor = df_filtrado[col].iloc[0]
if pd.notna(valor):
lucro_data.append({
"Indicador": col,
"Valor": formatar_moeda_brasil_correta(valor),
"Status": "✓"
})
else:
lucro_data.append({
"Indicador": f"{col}*",
"Valor": "Não calculado",
"Status": "✗"
})

if lucro_data:
lucro_df = pd.DataFrame(lucro_data)
st.dataframe(lucro_df[["Indicador", "Valor"]], use_container_width=True, hide_index=True)
else:
st.warning("Não há dados de lucro econômico disponíveis")

# Aba Fluxo de Caixa (sempre disponível)
with tab6:
st.subheader("💵 Fluxo de Caixa Operacional")

if 'Caixa Líquido Atividades Operacionais' in df_filtrado.columns:
valor_caixa = df_filtrado['Caixa Líquido Atividades Operacionais'].iloc[0]

if pd.notna(valor_caixa):
# KPI Principal
col1, col2, col3 = st.columns(3)

with col1:
st.metric("Caixa Operacional", formatar_moeda_brasil_correta(valor_caixa))

with col2:
# Comparação com Lucro Líquido
lucro_liquido = df_filtrado["Lucro/Prejuízo Consolidado do Período"].iloc[0] if pd.notna(df_filtrado["Lucro/Prejuízo Consolidado do Período"].iloc[0]) else 0
if lucro_liquido != 0:
relacao_caixa_lucro = (valor_caixa / lucro_liquido) * 100
st.metric("Caixa/Lucro", f"{relacao_caixa_lucro:.1f}%")

with col3:
# Comparação com EBITDA (apenas não bancos)
if not is_bank:
ebitda = df_filtrado["EBITDA"].iloc[0] if "EBITDA" in df_filtrado.columns and pd.notna(df_filtrado["EBITDA"].iloc[0]) else 0
if ebitda != 0:
relacao_caixa_ebitda = (valor_caixa / ebitda) * 100
st.metric("Caixa/EBITDA", f"{relacao_caixa_ebitda:.1f}%")
else:
st.metric("Caixa/EBITDA", "N/A (Banco)")

# Análise Qualitativa
st.subheader("📊 Análise do Fluxo de Caixa")

if valor_caixa > 0:
st.success("**✅ Geração Positiva de Caixa**")
st.write("A empresa está gerando caixa líquido positivo em suas atividades operacionais.")
else:
st.warning("**⚠️ Geração Negativa de Caixa**")
st.write("A empresa está consumindo caixa em suas atividades operacionais.")

# Comparação com indicadores de rentabilidade
if lucro_liquido != 0:
if abs(relacao_caixa_lucro - 100) > 50:
if relacao_caixa_lucro > 150:
st.info("**💡 Caixa > Lucro:** A empresa gera mais caixa que lucro contábil, indicando boa qualidade do lucro.")
elif relacao_caixa_lucro < 50:
st.warning("**💡 Caixa < Lucro:** A empresa gera menos caixa que lucro contábil, pode indicar diferenças temporárias ou baixa qualidade do lucro.")

else:
st.warning("Dados de Caixa Líquido de Atividades Operacionais não disponíveis para este ano")
else:
st.warning("Coluna 'Caixa Líquido Atividades Operacionais' não encontrada no dataset")

# Aba Dados Brutos (sempre disponível)
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

# Adicionar colunas específicas para bancos
if is_bank:
dados_brutos_cols.append("Resultado Abrangente do Período")

# Adicionar a coluna de depreciação/amortização se existir
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
if pd.notna(valor):
dados_brutos[col] = formatar_moeda_brasil_correta(valor)
else:
dados_brutos[col] = "N/A"

st.dataframe(pd.DataFrame.from_dict(dados_brutos, orient='index', columns=['Valor']), 
use_container_width=True)

else:
st.warning(f"Não há dados disponíveis para {ticker_selecionado} no ano {ano_selecionado}")

with tab_evolucao:
st.subheader(f"Evolução Temporal - {ticker_selecionado}")

if len(df_empresa_todos_anos) > 1:
# Verificar se é banco (para ocultar indicadores na evolução)
is_bank_series = df_empresa_todos_anos['is_bank'].iloc[0] if 'is_bank' in df_empresa_todos_anos.columns else False

# Gráficos de evolução temporal
col1, col2 = st.columns(2)

with col1:
# Rentabilidade
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
x=dados_validos['Ano'],
y=dados_validos[indicador],
mode='lines+markers',
name=indicador,
line=dict(color=cores[i % len(cores)], width=3),
marker=dict(size=8)
))

fig_rentabilidade.update_layout(
title='Evolução da Rentabilidade',
xaxis_title='Ano',
yaxis_title='Percentual',
yaxis_tickformat=',.2%',
height=400,
showlegend=True
)
st.plotly_chart(fig_rentabilidade, use_container_width=True)

with col2:
# Estrutura de Capital (apenas não bancos)
if not is_bank_series:
fig_estrutura = go.Figure()

indicadores_estrutura = ['Percentual Capital Terceiros', 'Percentual Capital Próprio']
cores_estrutura = ['#e74c3c', '#2ecc71']

for i, indicador in enumerate(indicadores_estrutura):
if indicador in df_empresa_todos_anos.columns:
dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
if not dados_validos.empty:
fig_estrutura.add_trace(go.Scatter(
x=dados_validos['Ano'],
y=dados_validos[indicador],
mode='lines+markers',
name=indicador,
line=dict(color=cores_estrutura[i % len(cores_estrutura)], width=3),
marker=dict(size=8),
stackgroup='one' if i == 0 else None
))

fig_estrutura.update_layout(
title='Evolução da Estrutura de Capital',
xaxis_title='Ano',
yaxis_title='Percentual',
yaxis_tickformat=',.2%',
height=400,
showlegend=True
)
st.plotly_chart(fig_estrutura, use_container_width=True)
else:
# Para bancos, mostrar evolução do PL médio
if 'PL Médio' in df_empresa_todos_anos.columns:
fig_pl = px.line(df_empresa_todos_anos, x='Ano', y='PL Médio',
   title='Evolução do Patrimônio Líquido Médio')
fig_pl.update_layout(yaxis_tickformat=',.0f')
st.plotly_chart(fig_pl, use_container_width=True)

# Segunda linha de gráficos (apenas não bancos)
if not is_bank_series:
col3, col4 = st.columns(2)

with col3:
# Custo de Capital
fig_custo = go.Figure()

indicadores_custo = ['ki', 'ke', 'wacc']
nomes_custo = ['Custo da Dívida (ki)', 'Custo do Capital Próprio (ke)', 'WACC']
cores_custo = ['#9b59b6', '#3498db', '#f39c12']

for i, indicador in enumerate(indicadores_custo):
if indicador in df_empresa_todos_anos.columns:
dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
if not dados_validos.empty:
fig_custo.add_trace(go.Scatter(
x=dados_validos['Ano'],
y=dados_validos[indicador],
mode='lines+markers',
name=nomes_custo[i],
line=dict(color=cores_custo[i % len(cores_custo)], width=3),
marker=dict(size=8)
))

fig_custo.update_layout(
title='Evolução do Custo de Capital',
xaxis_title='Ano',
yaxis_title='Percentual',
yaxis_tickformat=',.2%',
height=400,
showlegend=True
)
st.plotly_chart(fig_custo, use_container_width=True)

with col4:
# Margens
fig_margens = go.Figure()

indicadores_margens = ['Margem Bruta', 'Margem Operacional', 'Margem Líquida']
cores_margens = ['#16a085', '#27ae60', '#2980b9']

for i, indicador in enumerate(indicadores_margens):
if indicador in df_empresa_todos_anos.columns:
dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
if not dados_validos.empty:
fig_margens.add_trace(go.Scatter(
x=dados_validos['Ano'],
y=dados_validos[indicador],
mode='lines+markers',
name=indicador,
line=dict(color=cores_margens[i % len(cores_margens)], width=3),
marker=dict(size=8)
))

fig_margens.update_layout(
title='Evolução das Margens',
xaxis_title='Ano',
yaxis_title='Percentual',
yaxis_tickformat=',.2%',
height=400,
showlegend=True
)
st.plotly_chart(fig_margens, use_container_width=True)

# TERCEIRA LINHA - LUCRO ECONÔMICO E EBITDA (apenas não bancos)
if not is_bank_series:
st.subheader("💰 Evolução do Lucro Econômico e EBITDA")
col5, col6 = st.columns(2)

with col5:
# Lucro Econômico em valores absolutos
fig_lucro_absoluto = go.Figure()

indicadores_lucro = ['Lucro Econômico 1', 'Lucro Econômico 2']
nomes_lucro = ['Lucro Econômico 1', 'Lucro Econômico 2']
cores_lucro = ['#e74c3c', '#3498db']

for i, indicador in enumerate(indicadores_lucro):
if indicador in df_empresa_todos_anos.columns:
dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
if not dados_validos.empty:
fig_lucro_absoluto.add_trace(go.Scatter(
x=dados_validos['Ano'],
y=dados_validos[indicador],
mode='lines+markers',
name=nomes_lucro[i],
line=dict(color=cores_lucro[i % len(cores_lucro)], width=3),
marker=dict(size=8)
))

fig_lucro_absoluto.update_layout(
title='Lucro Econômico (Valores Absolutos)',
xaxis_title='Ano',
yaxis_title='Valor',
yaxis_tickformat=',.0f',
height=400,
showlegend=True
)
st.plotly_chart(fig_lucro_absoluto, use_container_width=True)

with col6:
# EBITDA vs Resultado Operacional
fig_ebitda = go.Figure()

indicadores_ebitda = ['EBITDA', 'Resultado Antes do Resultado Financeiro e dos Tributos']
nomes_ebitda = ['EBITDA', 'Resultado Operacional']
cores_ebitda = ['#2ecc71', '#34495e']

for i, indicador in enumerate(indicadores_ebitda):
if indicador in df_empresa_todos_anos.columns:
dados_validos = df_empresa_todos_anos[df_empresa_todos_anos[indicador].notna()]
if not dados_validos.empty:
fig_ebitda.add_trace(go.Scatter(
x=dados_validos['Ano'],
y=dados_validos[indicador],
mode='lines+markers',
name=nomes_ebitda[i],
line=dict(color=cores_ebitda[i % len(cores_ebitda)], width=3),
marker=dict(size=8)
))

fig_ebitda.update_layout(
title='EBITDA vs Resultado Operacional',
xaxis_title='Ano',
yaxis_title='Valor',
yaxis_tickformat=',.0f',
height=400,
showlegend=True
)
st.plotly_chart(fig_ebitda, use_container_width=True)

# QUARTA LINHA - FLUXO DE CAIXA OPERACIONAL
st.subheader("💸 Evolução do Fluxo de Caixa Operacional")
if 'Caixa Líquido Atividades Operacionais' in df_empresa_todos_anos.columns:
col7, col8 = st.columns(2)

with col7:
# Caixa Líquido Atividades Operacionais
fig_caixa = px.line(df_empresa_todos_anos, x='Ano', y='Caixa Líquido Atividades Operacionais',
  title='Caixa Líquido de Atividades Operacionais')
fig_caixa.update_layout(
yaxis_title='Caixa Operacional',
yaxis_tickformat=',.0f',
height=400
)
st.plotly_chart(fig_caixa, use_container_width=True)

with col8:
# Comparação Caixa vs Lucro Líquido
df_comparacao = df_empresa_todos_anos.copy()
df_comparacao = df_comparacao[df_comparacao['Caixa Líquido Atividades Operacionais'].notna() & 
            df_comparacao['Lucro/Prejuízo Consolidado do Período'].notna()]

if not df_comparacao.empty:
fig_comparacao = go.Figure()

fig_comparacao.add_trace(go.Scatter(
x=df_comparacao['Ano'],
y=df_comparacao['Caixa Líquido Atividades Operacionais'],
mode='lines+markers',
name='Caixa Operacional',
line=dict(color='#27ae60', width=3),
marker=dict(size=8)
))

fig_comparacao.add_trace(go.Scatter(
x=df_comparacao['Ano'],
y=df_comparacao['Lucro/Prejuízo Consolidado do Período'],
mode='lines+markers',
name='Lucro Líquido',
line=dict(color='#e74c3c', width=3),
marker=dict(size=8)
))

fig_comparacao.update_layout(
title='Comparação: Caixa Operacional vs Lucro Líquido',
xaxis_title='Ano',
yaxis_title='Valor',
yaxis_tickformat=',.0f',
height=400,
showlegend=True
)
st.plotly_chart(fig_comparacao, use_container_width=True)

# Tabela resumo da evolução
st.subheader("📋 Resumo da Evolução - Principais Indicadores")

# Selecionar indicadores chave para a tabela
if is_bank_series:
indicadores_resumo = ['ROE', 'ROA', 'Margem Bruta', 'Margem Operacional', 
'Resultado Abrangente do Período', 'PL Médio', 'Caixa Líquido Atividades Operacionais']
else:
indicadores_resumo = ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio', 
'Lucro Econômico 1', 'Resultado Antes do Resultado Financeiro e dos Tributos', 'EBITDA',
'Caixa Líquido Atividades Operacionais']

df_resumo = df_empresa_todos_anos[['Ano'] + [col for col in indicadores_resumo if col in df_empresa_todos_anos.columns]]

# Formatar para porcentagem e valores monetários
def formatar_valor(valor, coluna):
if coluna in ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio', 'Margem Bruta', 'Margem Operacional']:
return formatar_percentual_brasil(valor, 2) if pd.notna(valor) else "N/A"
elif coluna in ['Lucro Econômico 1', 'Resultado Antes do Resultado Financeiro e dos Tributos', 'EBITDA', 'Caixa Líquido Atividades Operacionais', 'PL Médio', 'Resultado Abrangente do Período']:
return formatar_moeda_brasil_correta(valor) if pd.notna(valor) else "N/A"
else:
return valor

# Aplicar formatação
df_resumo_formatado = df_resumo.copy()
for col in df_resumo_formatado.columns:
if col != 'Ano':
df_resumo_formatado[col] = df_resumo_formatado[col].apply(lambda x: formatar_valor(x, col))

st.dataframe(df_resumo_formatado, use_container_width=True)

else:
st.info("ℹ️ São necessários dados de múltiplos anos para análise de evolução temporal")

# ==============================
# TELA - ANÁLISE SETORIAL (ESCALAS CORRIGIDAS)
# ==============================
elif modo_analise == "🏭 Análise Setorial":
st.header(f"🏭 Análise Setorial - {setor_selecionado}")

if not df_setor_todos_anos.empty:
# Abas para análise atual vs evolução temporal
tab_atual_setor, tab_evolucao_setor = st.tabs(["📊 Análise do Ano", "📈 Evolução Temporal"])

with tab_atual_setor:
st.subheader(f"Ano {ano_selecionado}")

if not df_filtrado.empty:
# KPIs do Setor - ESCALAS CORRIGIDAS
col1, col2, col3, col4 = st.columns(4)

with col1:
empresas_setor = df_filtrado["Ticker"].nunique()
st.metric("Empresas no Setor", empresas_setor)

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

# Verificar se o setor selecionado é bancos
is_bank_setor = setor_selecionado.lower() in ['bancos', 'instituição financeira', 'financeiro']

# Top empresas do setor por ROE
st.subheader("Top 10 Empresas do Setor por ROE")
top_roe_setor = df_filtrado[df_filtrado["ROE"].notna()].nlargest(10, "ROE")[["Ticker", "ROE"]]

if not top_roe_setor.empty:
fig_roe = px.bar(top_roe_setor, x="Ticker", y="ROE", 
title="ROE por Empresa no Setor")
fig_roe.update_layout(yaxis_tickformat=',.2%')
st.plotly_chart(fig_roe, use_container_width=True)
else:
st.warning("Não há dados de ROE disponíveis para este setor")

# Comparativo de estrutura de capital no setor (apenas não bancos)
if not is_bank_setor:
st.subheader("Estrutura de Capital no Setor")
estrutura_setor = df_filtrado[df_filtrado["Percentual Capital Próprio"].notna()].nlargest(15, "Patrimônio Líquido Consolidado")

if not estrutura_setor.empty:
fig_estrutura = px.bar(estrutura_setor, 
     x="Ticker", 
     y=["Percentual Capital Terceiros", "Percentual Capital Próprio"],
     title="Estrutura de Capital das Principais Empresas do Setor",
     barmode='stack')
fig_estrutura.update_layout(yaxis_tickformat=',.2%')
st.plotly_chart(fig_estrutura, use_container_width=True)
else:
st.warning("Não há dados de estrutura de capital disponíveis para este setor")
else:
st.info("ℹ️ Análise de estrutura de capital não se aplica a bancos.")

# Ranking de rentabilidade no setor
st.subheader("Ranking de Rentabilidade no Setor")
if is_bank_setor:
rentabilidade_setor = df_filtrado[
df_filtrado["ROE"].notna() & 
df_filtrado["ROA"].notna()
].nlargest(15, "ROE")[["Ticker", "ROE", "ROA"]]
else:
rentabilidade_setor = df_filtrado[
df_filtrado["ROE"].notna() & 
df_filtrado["ROA"].notna() & 
df_filtrado["ROI"].notna()
].nlargest(15, "ROE")[["Ticker", "ROE", "ROA", "ROI", "Margem Líquida"]]

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
# Calcular médias do setor por ano
if is_bank_setor:
indicadores_setor = ['ROE', 'ROA', 'Margem Bruta', 'Margem Operacional', 'Resultado Abrangente do Período', 'PL Médio']
else:
indicadores_setor = ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio', 'Lucro Econômico 1', 'EBITDA']

# Agrupar por ano e calcular mediana (menos sensível a outliers)
df_setor_evolucao = df_setor_todos_anos.groupby('Ano')[indicadores_setor].median().reset_index()

# Gráficos de evolução do setor
col1, col2 = st.columns(2)

with col1:
# Rentabilidade do setor
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
x=dados_validos['Ano'],
y=dados_validos[indicador],
mode='lines+markers',
name=indicador,
line=dict(color=cores_setor[i % len(cores_setor)], width=3),
marker=dict(size=8)
))

fig_setor_rent.update_layout(
title='Evolução da Rentabilidade do Setor (Mediana)',
xaxis_title='Ano',
yaxis_title='Percentual',
yaxis_tickformat=',.2%',
height=400,
showlegend=True
)
st.plotly_chart(fig_setor_rent, use_container_width=True)

with col2:
# Estrutura e custo do setor (apenas não bancos)
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
x=dados_validos['Ano'],
y=dados_validos[indicador],
mode='lines+markers',
name=nomes_estrutura[i],
line=dict(color=cores_estrutura_setor[i % len(cores_estrutura_setor)], width=3),
marker=dict(size=8)
))

fig_setor_estrutura.update_layout(
title='Evolução da Estrutura e Custo de Capital (Mediana)',
xaxis_title='Ano',
yaxis_title='Percentual',
yaxis_tickformat=',.2%',
height=400,
showlegend=True
)
st.plotly_chart(fig_setor_estrutura, use_container_width=True)
else:
# Para bancos, mostrar evolução do PL médio
if 'PL Médio' in df_setor_evolucao.columns:
fig_pl_setor = px.line(df_setor_evolucao, x='Ano', y='PL Médio',
          title='Evolução do PL Médio (Mediana)')
fig_pl_setor.update_layout(yaxis_tickformat=',.0f')
st.plotly_chart(fig_pl_setor, use_container_width=True)

# TERCEIRA LINHA - LUCRO ECONÔMICO E EBITDA (apenas não bancos)
if not is_bank_setor:
st.subheader("💰 Evolução do Lucro Econômico e EBITDA no Setor")
col3, col4 = st.columns(2)

with col3:
# Lucro Econômico médio do setor
if 'Lucro Econômico 1' in df_setor_evolucao.columns:
fig_setor_lucro = px.line(df_setor_evolucao, x='Ano', y='Lucro Econômico 1',
            title='Lucro Econômico Médio do Setor (Mediana)')
fig_setor_lucro.update_layout(
yaxis_title='Lucro Econômico',
yaxis_tickformat=',.0f',
height=400
)
st.plotly_chart(fig_setor_lucro, use_container_width=True)

with col4:
# EBITDA médio do setor
if 'EBITDA' in df_setor_evolucao.columns:
fig_setor_ebitda = px.line(df_setor_evolucao, x='Ano', y='EBITDA',
             title='EBITDA Médio do Setor (Mediana)')
fig_setor_ebitda.update_layout(
yaxis_title='EBITDA',
yaxis_tickformat=',.0f',
height=400
)
st.plotly_chart(fig_setor_ebitda, use_container_width=True)

# Tabela resumo da evolução do setor
st.subheader("📋 Resumo da Evolução do Setor - Principais Indicadores")

# Formatar para porcentagem e valores monetários
def formatar_valor_setor(valor, coluna):
if coluna in ['ROE', 'ROA', 'ROI', 'Margem Líquida', 'wacc', 'Percentual Capital Próprio', 'Margem Bruta', 'Margem Operacional']:
return formatar_percentual_brasil(valor, 2) if pd.notna(valor) else "N/A"
elif coluna in ['Lucro Econômico 1', 'EBITDA', 'PL Médio', 'Resultado Abrangente do Período']:
return formatar_moeda_brasil_correta(valor) if pd.notna(valor) else "N/A"
else:
return valor

# Aplicar formatação
df_setor_formatado = df_setor_evolucao.copy()
for col in df_setor_formatado.columns:
if col != 'Ano':
df_setor_formatado[col] = df_setor_formatado[col].apply(lambda x: formatar_valor_setor(x, col))

st.dataframe(df_setor_formatado, use_container_width=True)

# Dispersão do setor
st.subheader("📊 Dispersão de Rentabilidade no Setor")

if ano_selecionado in df_setor_todos_anos['Ano'].values:
df_setor_ano = df_setor_todos_anos[df_setor_todos_anos['Ano'] == ano_selecionado]

if not df_setor_ano.empty and 'ROE' in df_setor_ano.columns:
fig_dispersao = px.box(df_setor_ano, y='ROE', 
     title=f'Distribuição do ROE no Setor - {ano_selecionado}')
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

# Exibir fórmulas em colunas
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

# Rodapé
st.divider()
st.caption(f"📊 Dashboard CVM - Indicadores Financeiros | Dados atualizados para {ano_selecionado} | Total de empresas na base: {df['Ticker'].nunique()}")

# Adicionar informações sobre os cálculos
with st.sidebar.expander("💡 Teste Livro utilizado: Análise das Demonstrações Finaneiras. Editora Viena. 2024. Autor Cassio Luiz Vellani. (VELLANI, 2024)"):
st.write("""
**Cálculos Verificados:**

**VERIFICAÇÃO:**
- Lucro Econômico 1 IGUAL ao Lucro Econômico 2 (para não bancos)

**Consistência Garantida:**
- ROI = Resultado Operacional ÷ Investimento Médio (NÃO para bancos)
- Lucro Econômico 1 = (ROI - WACC) × Investimento Médio (NÃO para bancos)
- Lucro Econômico 2 = Resultado Operacional - (WACC × Investimento Médio) (NÃO para bancos)
- **RESULTADO:** Lucro Econômico 1 = Lucro Econômico 2 (para não bancos)

**EBITDA Corrigido (para não bancos):**
- **EXCLUSIVAMENTE** usando a coluna 'Depreciação e amortização'
- **CORREÇÃO:** Usa valores absolutos para depreciação/amortização para garantir cálculo correto
- **FÓRMULA:** EBITDA = Resultado Operacional + |Depreciação e Amortização|

**Valuation Lucro Econômico/SELIC (para não bancos):**
- **FÓRMULA CORRETA:** Valor da Empresa = Lucro Econômico ÷ (SELIC/100)
- **CONVERSÃO:** Valor em R$ mil convertido para R$ normais (×1000)
- **COTAÇÃO ESPERADA:** Valor da Empresa (R$) ÷ Número de Ações
- **COTAÇÃO:** Busca em tempo real via Yahoo Finance
- **ANÁLISE:** Comparação entre valuation calculado e cotação de mercado

**Valuation para Bancos (Vellani, 2024):**
- **FÓRMULA:** (LPA - (VPA × r)) / r
- **LPA = Resultado Abrangente ÷ Número de Ações**
- **VPA = PL Médio ÷ Número de Ações**
- **r = taxa de desconto (SELIC)**

**Novas Funcionalidades:**
- **FLUXO DE CAIXA OPERACIONAL:** Adicionada análise do Caixa Líquido de Atividades Operacionais
- **COMPARAÇÃO:** Caixa Operacional vs Lucro Líquido para análise de qualidade do lucro
- **EVOLUÇÃO TEMPORAL:** Gráficos de fluxo de caixa na análise histórica
- **SUPORTE A BANCOS:** Ocultação de indicadores não aplicáveis e valuation específico

**Dataset: dff_2010_2025**
- Período: 2010-2025 (16 anos)
- Empresas: 2.566 únicas
- Setores: 70 categorias
- **ESCALA DOS VALORES NO DATASET:** R$ mil
- **NÚMERO DE AÇÕES:** Pode ser obtido via Yahoo Finance ou do dataset (se disponível)
""")
