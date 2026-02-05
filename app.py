import streamlit as st
import psycopg2
import pandas as pd
import os
import base64
from datetime import datetime
from decimal import Decimal
import warnings

# --- 1. CONFIGURAÇÃO GERAL ---
st.set_page_config(page_title="Abastecimento Seguro", layout="wide", initial_sidebar_state="collapsed")
warnings.filterwarnings('ignore')

# Pasta de fotos (Cria se não existir)
PASTA_FOTOS = "fotos_abastecimento"
if not os.path.exists(PASTA_FOTOS):
    os.makedirs(PASTA_FOTOS)

# --- 2. BANCO DE DADOS (CONEXÃO HÍBRIDA: NUVEM/LOCAL) ---
def init_connection():
    """
    Conecta ao banco. Prioriza a URL da Render. Se não achar, tenta localhost.
    """
    db_url = os.getenv("DATABASE_URL")
    
    try:
        if db_url:
            return psycopg2.connect(db_url)
        else:
            return psycopg2.connect(host="localhost", database="Combustivel", user="postgres", password="admin")
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        st.stop()

# --- 3. AUTO-MIGRATION (ESSENCIAL PARA RENDER) ---
# Esta função cria a tabela sozinha se ela não existir no banco novo
def criar_tabelas_se_nao_existirem():
    conn = init_connection()
    cursor = conn.cursor()
    query_criar = """
    CREATE TABLE IF NOT EXISTS registro_abastecimento (
        id SERIAL PRIMARY KEY,
        apartamento_id INT DEFAULT 1,
        placa VARCHAR(20),
        km_veiculo INT,
        leitura_inicial DECIMAL(10,2),
        leitura_final DECIMAL(10,2),
        litros_total DECIMAL(10,2),
        foto_km_path TEXT,
        foto_inicial_path TEXT,
        foto_final_path TEXT,
        data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    cursor.execute(query_criar)
    conn.commit()
    conn.close()

# Executa a verificação do banco assim que o app liga
criar_tabelas_se_nao_existirem()

# --- 4. FUNÇÕES DE SUPORTE ---
def salvar_abastecimento(dados):
    conn = init_connection()
    cursor = conn.cursor()
    try:
        query = """
        INSERT INTO registro_abastecimento 
        (apartamento_id, placa, km_veiculo, leitura_inicial, leitura_final, litros_total, foto_km_path, foto_inicial_path, foto_final_path)
        VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            dados['placa'], dados['km'], dados['inicio'], dados['fim'], dados['litros'],
            dados['f_km'], dados['f_ini'], dados['f_fim']
        ))
        conn.commit()
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
    finally:
        conn.close()

def listar_historico_completo():
    conn = init_connection()
    query = """
    SELECT data_hora, placa, km_veiculo, leitura_inicial, leitura_final, litros_total, 
           foto_km_path, foto_inicial_path, foto_final_path 
    FROM registro_abastecimento ORDER BY id DESC LIMIT 50
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def salvar_foto(foto, nome):
    if foto is None: return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"{nome}_{timestamp}.jpg"
    caminho = os.path.join(PASTA_FOTOS, nome_arquivo)
    with open(caminho, "wb") as f:
        f.write(foto.getbuffer())
    return caminho

def converter_imagem_para_base64(caminho_arquivo):
    if caminho_arquivo and os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return f"data:image/jpeg;base64,{encoded}"
    return None

# --- 5. CSS PROFISSIONAL ---
st.markdown("""
<style>
    .stApp { background-color: #f1f8e9; }
    h1, h2, h3 { color: #2e7d32 !important; font-weight: 800; }
    .stTextInput label, .stNumberInput label { color: #1b5e20 !important; font-weight: bold; font-size: 16px; }
    
    .stTextInput input, .stNumberInput input {
        background-color: white !important; color: #1b5e20 !important;
        border: 2px solid #a5d6a7 !important; border-radius: 10px !important;
        height: 50px; font-size: 18px !important; font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #2e7d32 !important; box-shadow: 0 0 0 2px rgba(46, 125, 50, 0.2) !important;
    }

    /* Botões */
    button[kind="primary"] {
        background: linear-gradient(45deg, #2e7d32, #43a047) !important;
        color: white !important; border: none !important; border-radius: 12px !important;
        height: 60px !important; font-size: 20px !important; font-weight: bold !important;
        text-transform: uppercase; width: 100%; box-shadow: 0 4px 10px rgba(46, 125, 50, 0.3);
        transition: transform 0.2s;
    }
    button[kind="primary"]:active { transform: scale(0.98); }

    button[kind="secondary"] {
        border: 2px solid #ef5350 !important; color: #ef5350 !important;
        background-color: white !important; font-weight: bold; border-radius: 10px;
    }

    div[data-testid="stCameraInput"] {
        background-color: white; padding: 10px; border-radius: 12px;
        border: 2px dashed #81c784; margin-top: 10px; margin-bottom: 20px;
    }

    [data-testid="stSidebar"] {display: none;}
    #MainMenu {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 6. CONTROLE DE ESTADO ---
if 'pagina' not in st.session_state: st.session_state.pagina = 'home'
if 'reset_id' not in st.session_state: st.session_state.reset_id = 0

def limpar_tela():
    st.session_state.reset_id += 1

# =======================================================
# TELA 1: HOME (FLUXO CIRÚRGICO)
# =======================================================
if st.session_state.pagina == 'home':
    rid = st.session_state.reset_id
    
    # Cabeçalho
    c1, c2, c3 = st.columns([6, 2, 1])
    with c1: st.markdown("### ⛽ Novo Abastecimento")
    with c2: st.button("🗑️ Limpar", on_click=limpar_tela, type="secondary", use_container_width=True)
    with c3:
        if st.button("⚙️"):
            st.session_state.pagina = 'login'
            st.rerun()

    # Container Principal
    with st.container():
        # 1. Placa
        placa = st.text_input("1. Placa do Veículo", placeholder="Ex: ABC-1234", key=f"placa_{rid}").upper()
        
        if placa:
            # 2. KM
            km = st.number_input("2. Odômetro (KM)", min_value=0, step=1, key=f"km_{rid}")
            
            if km > 0:
                st.caption("📸 Tire a foto do Painel para liberar o próximo campo:")
                foto_km = st.camera_input("foto_km", key=f"cam_km_{rid}", label_visibility="collapsed")
                
                if foto_km:
                    st.success("Foto KM OK! ✅")
                    st.markdown("---") 
                    
                    # 3. Inicial
                    inicio = st.number_input("3. Leitura Inicial (Bomba)", min_value=0.0, format="%.2f", key=f"ini_{rid}")
                    
                    if inicio > 0:
                        st.caption("📸 Tire a foto da Bomba (Início) para continuar:")
                        foto_ini = st.camera_input("foto_ini", key=f"cam_ini_{rid}", label_visibility="collapsed")
                        
                        if foto_ini:
                            st.success("Foto Início OK! ✅")
                            st.markdown("---")
                            
                            # 4. Final
                            fim = st.number_input("4. Leitura Final (Bomba)", min_value=0.0, format="%.2f", key=f"fim_{rid}")
                            
                            if fim > 0:
                                st.caption("📸 Tire a foto da Bomba (Final) para finalizar:")
                                foto_fim = st.camera_input("foto_fim", key=f"cam_fim_{rid}", label_visibility="collapsed")
                                
                                if foto_fim:
                                    st.success("Foto Final OK! ✅")
                                    
                                    # Cálculo
                                    litros = Decimal('0.00')
                                    if fim > inicio:
                                        litros = Decimal(str(fim)) - Decimal(str(inicio))
                                        
                                        st.markdown(f"""
                                        <div style="background-color: #c8e6c9; padding: 20px; border-radius: 10px; text-align: center; margin-top: 10px;">
                                            <h2 style="margin:0; color: #1b5e20;">Total: {litros} Litros</h2>
                                        </div>
                                        """, unsafe_allow_html=True)

                                        # Salvar
                                        if st.button("✔ SALVAR REGISTRO", type="primary"):
                                            dados = {
                                                'placa': placa, 'km': km, 'inicio': inicio, 'fim': fim, 'litros': litros,
                                                'f_km': salvar_foto(foto_km, "KM"),
                                                'f_ini': salvar_foto(foto_ini, "INI"),
                                                'f_fim': salvar_foto(foto_fim, "FIM")
                                            }
                                            salvar_abastecimento(dados)
                                            st.balloons()
                                            st.success("✅ Registro Salvo com Sucesso!")
                                            st.button("🔄 Novo Abastecimento (Limpar)", on_click=limpar_tela, type="primary")
                                    else:
                                        st.warning("⚠️ A Leitura Final deve ser maior que a Inicial.")
                                else:
                                    st.info("👆 Tire a foto final para habilitar o botão de Salvar.")
                            else:
                                st.info("Digite a leitura final para liberar a câmera.")
                        else:
                            st.info("👆 Tire a foto inicial para liberar a leitura final.")
                    else:
                        st.info("Digite a leitura inicial para liberar a câmera.")
                else:
                    st.info("👆 Tire a foto do KM para liberar o próximo campo.")
            else:
                st.write("") 
        else:
            st.write("")

# =======================================================
# TELA 2: LOGIN ADMIN
# =======================================================
elif st.session_state.pagina == 'login':
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("### 🔒 Acesso Gerencial")
        senha = st.text_input("Senha:", type="password")
        col_a, col_b = st.columns(2)
        if col_a.button("Voltar"):
            st.session_state.pagina = 'home'
            st.rerun()
        if col_b.button("Entrar", type="primary"):
            if senha == "admin":
                st.session_state.pagina = 'historico'
                st.rerun()
            else:
                st.error("Senha incorreta")

# =======================================================
# TELA 3: RELATÓRIO COMPLETO
# =======================================================
elif st.session_state.pagina == 'historico':
    c_back, c_title = st.columns([1, 6])
    with c_back:
        if st.button("⬅️ Voltar"):
            st.session_state.pagina = 'home'
            st.rerun()
    with c_title:
        st.markdown("### 📋 Histórico Completo")

    df = listar_historico_completo()
    
    if not df.empty:
        df['data_hora'] = pd.to_datetime(df['data_hora']).dt.strftime('%d/%m %H:%M')
        
        # Converte imagens
        df['foto_km_path'] = df['foto_km_path'].apply(converter_imagem_para_base64)
        df['foto_inicial_path'] = df['foto_inicial_path'].apply(converter_imagem_para_base64)
        df['foto_final_path'] = df['foto_final_path'].apply(converter_imagem_para_base64)

        df = df.rename(columns={
            'data_hora': 'Data', 'placa': 'Placa', 'km_veiculo': 'KM',
            'litros_total': 'Litros', 'leitura_inicial': 'Inicial', 'leitura_final': 'Final',
            'foto_km_path': 'Foto KM', 'foto_inicial_path': 'Foto Ini', 'foto_final_path': 'Foto Fim'
        })

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Data": st.column_config.TextColumn("Data", width="small"),
                "Placa": st.column_config.TextColumn("Placa", width="small"),
                "KM": st.column_config.NumberColumn("KM", format="%d"),
                "Litros": st.column_config.NumberColumn("Litros", format="%.2f L"),
                "Inicial": st.column_config.NumberColumn("Ini", format="%.1f"),
                "Final": st.column_config.NumberColumn("Fim", format="%.1f"),
                "Foto KM": st.column_config.ImageColumn("Painel", width="small"),
                "Foto Ini": st.column_config.ImageColumn("Bomba Ini", width="small"),
                "Foto Fim": st.column_config.ImageColumn("Bomba Fim", width="small")
            }
        )
    else:
        st.info("Nenhum registro encontrado.")