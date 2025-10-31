import streamlit as st
import mysql.connector
from mysql.connector import Error
import datetime
import locale  # Necessário para obter o nome do dia em português


# --- Configuração do Banco de Dados ---
# Usaremos o @st.cache_resource para não abrir e fechar a conexão toda hora
@st.cache_resource
def create_db_connection():
    try:
        conn = mysql.connector.connect(
            host=st.secrets.mysql.host,
            port=st.secrets.mysql.port,
            database=st.secrets.mysql.database,
            user=st.secrets.mysql.user,
            password=st.secrets.mysql.password
        )
        return conn
    except Error as e:
        st.error(f"Erro ao conectar ao MySQL: {e}")
        return None


# --- Funções de Lógica ---

def get_dia_semana_hoje():
    """Retorna o nome do dia da semana de hoje em PT-BR, ou None se for Fim de Semana."""
    try:
        # Tenta configurar para português
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
        except locale.Error:
            pass  # Continua com o padrão se não conseguir

    hoje = datetime.date.today()
    dia_nome = hoje.strftime('%A').title()  # Ex: Segunda-feira

    # Se for Fim de Semana, retorna None (para não buscar tarefas)
    if hoje.weekday() >= 5:  # 5 é Sábado, 6 é Domingo
        return None

    # Retorna o nome no formato do ENUM do banco (ex: "Segunda-feira")
    return dia_nome


def get_criancas(conn):
    # Busca todas as crianças cadastradas
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nome FROM criancas")
    return cursor.fetchall()


def get_tarefas_do_dia_com_nomes(conn, crianca_id, dia_semana_nome):
    """
    Busca as tarefas do dia usando JOIN para pegar os nomes,
    filtrando pela criança e pelo nome do dia.
    """
    query = """
    SELECT 
        a.id AS agenda_id, 
        t.descricao AS nome_da_tarefa, 
        a.status
    FROM agenda_tarefas AS a
    JOIN tarefas AS t ON a.tarefa_id = t.id
    WHERE 
        a.crianca_id = %s 
        AND a.dia_semana = %s
        -- Garante que a tarefa está pendente OU que é um novo dia, 
        -- para que o status não fique preso em 'concluida' de um dia anterior.
        AND (a.data_tarefa != CURDATE() OR a.status = 'pendente')
    ORDER BY a.id
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (crianca_id, dia_semana_nome))
    return cursor.fetchall()


def marcar_tarefa(conn, agenda_id, novo_status):
    # Atualiza o status e a data da tarefa
    status_str = 'concluida' if novo_status else 'pendente'
    data_hoje = datetime.date.today()

    query = """
    UPDATE agenda_tarefas 
    SET status = %s, data_tarefa = %s 
    WHERE id = %s
    """
    cursor = conn.cursor()
    cursor.execute(query, (status_str, data_hoje, agenda_id))
    conn.commit()


# --- Interface do Streamlit ---

st.set_page_config(page_title="Tarefas de Casa", layout="wide")
st.title("📋 Quadro de Tarefas da Família")

conn = create_db_connection()

if not conn or not conn.is_connected():
    st.error("Não foi possível conectar ao banco de dados.")
else:
    dia_semana_nome = get_dia_semana_hoje()
    hoje_str = datetime.date.today().strftime('%d/%m/%Y')

    if dia_semana_nome is None:
        st.balloons()
        st.success(f"Hoje é {hoje_str}. Bom fim de semana! Sem tarefas hoje. 🎉")
    else:
        st.header(f"Tarefas de Hoje: {dia_semana_nome} ({hoje_str})", divider="rainbow")

        lista_criancas = get_criancas(conn)

        # Cria colunas para cada criança (max 3 colunas por questão de espaço)
        num_cols = min(len(lista_criancas), 3)
        colunas = st.columns(num_cols)

        for i, crianca in enumerate(lista_criancas):
            # i % num_cols garante que o índice da coluna se repete
            with colunas[i % num_cols]:
                st.subheader(f"Para: {crianca['nome']}")

                # BUSCA DE DADOS COM JOIN
                tarefas = get_tarefas_do_dia_com_nomes(conn, crianca['id'], dia_semana_nome)

                if not tarefas:
                    st.info(f"{crianca['nome']} não tem tarefas agendadas para {dia_semana_nome}.")
                else:
                    for tarefa in tarefas:
                        tarefa_feita_hoje = (tarefa['status'] == 'concluida')
                        key_tarefa = f"tarefa_{tarefa['agenda_id']}"

                        # Usa o nome real da tarefa que veio do JOIN: tarefa['nome_da_tarefa']
                        status_atual = st.checkbox(
                            tarefa['nome_da_tarefa'],
                            value=tarefa_feita_hoje,
                            key=key_tarefa
                        )

                        if status_atual != tarefa_feita_hoje:
                            marcar_tarefa(conn, tarefa['agenda_id'], status_atual)
                            st.rerun()  # Recarrega para atualizar o estado