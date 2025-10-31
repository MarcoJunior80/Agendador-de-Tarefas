import mysql.connector
from mysql.connector import Error
import datetime
import telegram
import asyncio
import locale
import os  # Para simular o st.secrets fora do Streamlit


# --- Simulação dos Secrets para Rodar Fora do Streamlit ---
# Em um ambiente de produção (Crontab), não teremos st.secrets.
# A forma mais robusta é ler de variáveis de ambiente.
# Para manter a simplicidade, vamos usar um 'dummy'
# Em produção, você deve substituir essas linhas por variáveis de ambiente ou por leitura do secrets.toml

class DummySecrets:
    @property
    def mysql(self):
        # NOTA: Em produção, estas variáveis DEVEM vir de um lugar seguro (ex: os.environ)
        return type('MySQL', (object,), {
            'host': 'localhost',
            'port': 3306,
            'database': 'casa_automacao',
            'user': 'root',
            'password': 'Manaj@1709'
        })()

    @property
    def telegram(self):
        return type('Telegram', (object,), {
            'token': '8286854492:AAGJSp_zQ5esM2a0d_T4ok01Ff2YuFEF6_U',
            'chat_id': '-1003284500478'
        })()


# Use o st.secrets no Streamlit, use a simulação ou variáveis de ambiente no notificar.py
SECRETS = DummySecrets()


# --- Funções de Conexão e Lógica (Reutilizadas do app.py) ---

def create_db_connection():
    try:
        # Usa os SECRETS simulados ou reais
        conn = mysql.connector.connect(
            host=SECRETS.mysql.host,
            port=SECRETS.mysql.port,
            database=SECRETS.mysql.database,
            user=SECRETS.mysql.user,
            password=SECRETS.mysql.password
        )
        return conn
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
        return None


def get_dia_semana_hoje():
    """Retorna o nome do dia da semana de hoje em PT-BR, ou None se for Fim de Semana."""
    try:
        # Tenta configurar para português
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
        except locale.Error:
            pass

    hoje = datetime.date.today()
    dia_nome = hoje.strftime('%A').title()

    if hoje.weekday() >= 5:  # Sábado (5) ou Domingo (6)
        return None

    return dia_nome


def get_tarefas_para_notificar(conn, dia_semana_nome):
    """
    Busca todas as tarefas de todas as crianças para o dia de hoje,
    incluindo o nome e o número de WhatsApp/Telegram.
    """
    query = """
    SELECT 
        c.nome AS nome_da_crianca, 
        t.descricao AS nome_da_tarefa
    FROM agenda_tarefas AS a
    JOIN criancas AS c ON a.crianca_id = c.id
    JOIN tarefas AS t ON a.tarefa_id = t.id
    WHERE 
        a.dia_semana = %s
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (dia_semana_nome,))
    return cursor.fetchall()


# --- Funções de Notificação Telegram ---

async def enviar_via_telegram(texto):
    """Função assíncrona para enviar a mensagem via bot do Telegram."""
    try:
        token = SECRETS.telegram.token
        chat_id = SECRETS.telegram.chat_id

        bot = telegram.Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=texto, parse_mode='Markdown')
        print("Mensagem enviada com sucesso via Telegram.")

    except Exception as e:
        print(f"Falha ao enviar via Telegram. Verifique Token e Chat ID. Erro: {e}")


def main_notificar():
    """Função principal que orquestra a busca e o envio."""
    conn = create_db_connection()
    if not conn:
        return

    dia_semana_nome = get_dia_semana_hoje()

    if dia_semana_nome is None:
        print("Fim de semana. Sem notificações.")
        conn.close()
        return

    tarefas = get_tarefas_para_notificar(conn, dia_semana_nome)
    conn.close()

    if not tarefas:
        print(f"Nenhuma tarefa agendada para {dia_semana_nome}.")
        return

    # 1. Agrupa tarefas por nome da criança
    tarefas_por_crianca = {}
    for tarefa in tarefas:
        nome = tarefa['nome_da_crianca']
        if nome not in tarefas_por_crianca:
            tarefas_por_crianca[nome] = []
        tarefas_por_crianca[nome].append(tarefa['nome_da_tarefa'])

    # 2. Constrói a mensagem
    mensagem_final = f"Bom dia, Crianças! ☀️\n\n*Tarefas de {dia_semana_nome.upper()}:*\n\n"

    for nome, lista_tarefas in tarefas_por_crianca.items():
        mensagem_final += f"*{nome}:*\n"
        for t in lista_tarefas:
            mensagem_final += f"- {t}\n"
        mensagem_final += "\n"

    # Mensagem finaliza com uma chamada para a ação no Streamlit
    mensagem_final += "Lembrem-se de checar o painel para marcar como concluído! 😉"

    # 3. Envia a mensagem (o Telegram usa o asyncio)
    asyncio.run(enviar_via_telegram(mensagem_final))


if __name__ == "__main__":
    main_notificar()