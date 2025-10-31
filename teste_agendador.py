
import time
import schedule
import datetime
import subprocess
import sys

# O caminho para o seu script notificar.py
NOTIFICAR_SCRIPT = r"C:\Users\marco\PycharmProjects\Tarefas_Casa\notificar.py"

def job():
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Iniciando notificação...")
    try:
        # Executa o notificar.py usando o Python que está rodando este scheduler
        subprocess.run([sys.executable, NOTIFICAR_SCRIPT], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar notificar.py: {e}")

# Agenda para rodar de Segunda a Sexta às 8:00
schedule.every().monday.at("08:00").do(job)
schedule.every().tuesday.at("08:00").do(job)
schedule.every().wednesday.at("08:00").do(job)
schedule.every().thursday.at("08:00").do(job)
schedule.every().friday.at("08:00").do(job)

print("Agendador de tarefas iniciado. Aguardando horário...")

while True:
    schedule.run_pending()
    time.sleep(60) # Verifica o agendamento a cada 60 segundos