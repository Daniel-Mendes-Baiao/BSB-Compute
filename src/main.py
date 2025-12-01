import json, time, os
from multiprocessing import Queue
from scheduler import Scheduler
from worker import iniciar_workers
from ipc import enviar_tarefa, receber_resposta
from utils import ts


def carregar_config():
    # Mesmo padrão do seu projeto: config.json na pasta acima de src
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def prioridade_label(n):
    return {1: "Alta", 2: "Média", 3: "Baixa"}.get(n, "?")


def executar_politica(policy, cfg):
    print("\n" + "=" * 60)
    print(f"=== INICIANDO SIMULAÇÃO: {policy.upper()} ===")
    print("=" * 60)

    start = time.time()
    quantum = cfg["quantum"]

    # Cada requisição vira uma tarefa pendente
    # last_worker: guarda o último servidor que executou essa tarefa
    pending = [{
        **r,
        "arrival_time": start,
        "remaining": r["tempo_exec"],
        "running": False,
        "last_worker": None
    } for r in cfg["requisicoes"]]

    retorno = Queue()
    filas = {s["id"]: Queue() for s in cfg["servidores"]}
    estados = {s["id"]: {"cap": s["capacidade"], "load": 0, "busy": 0} for s in cfg["servidores"]}

    iniciar_workers(cfg["servidores"], filas, retorno)
    scheduler = Scheduler(policy)
    completed = {}

    while True:
        now = time.time()
        elapsed = now - start

        # Tarefas elegíveis: não estão rodando e ainda têm tempo restante
        elegiveis = [t for t in pending if not t["running"] and t["remaining"] > 0]
        scheduler.reorder(elegiveis)

        # Servidores com espaço disponível (load < capacidade)
        livres = [sid for sid, st in estados.items() if st["load"] < st["cap"]]

        # ============================
        # ATRIBUIR TAREFAS A SERVIDORES
        # ============================
        while elegiveis and livres:
            t = scheduler.next_task(elegiveis)

            # *** LÓGICA DE MIGRAÇÃO AQUI ***
            # Se a tarefa já rodou em algum servidor (last_worker != None),
            # tentamos mandá-la para um servidor DIFERENTE (migração).
            if t["last_worker"] is not None:
                # candidatos = servidores livres diferentes do último servidor
                candidatos = [sid for sid in livres if sid != t["last_worker"]]
                if candidatos:
                    # escolhe o menos carregado entre os candidatos
                    sid = min(candidatos, key=lambda x: estados[x]["load"])
                else:
                    # se só tiver o mesmo servidor livre, vai nele mesmo
                    sid = min(livres, key=lambda x: estados[x]["load"])
            else:
                # primeira execução dessa tarefa
                sid = min(livres, key=lambda x: estados[x]["load"])

            t["running"] = True

            # primeira vez que a tarefa entra no sistema
            if t["id"] not in completed:
                completed[t["id"]] = {"arrival": t["arrival_time"], "end": None}

            msg = {
                "id": t["id"],
                "priority": t["prioridade"],
                "remaining": t["remaining"]
            }

            if policy == "rr":
                msg["slice"] = min(quantum, t["remaining"])
            else:
                msg["exec_time"] = t["remaining"]

            enviar_tarefa(filas[sid], msg)
            estados[sid]["load"] += 1

            # ***** DETECÇÃO E LOG DE MIGRAÇÃO *****
            if t["last_worker"] is not None and t["last_worker"] != sid:
                # A tarefa estava em um servidor e foi para outro -> MIGRAÇÃO
                print(
                    f"{ts(elapsed)} MIGRAÇÃO: Requisição {t['id']} "
                    f"({prioridade_label(t['prioridade'])}) "
                    f"do Servidor {t['last_worker']} para o Servidor {sid} "
                    f"[{policy.upper()}]"
                )
            else:
                # Atribuição normal (sem migração)
                print(
                    f"{ts(elapsed)} Requisição {t['id']} "
                    f"({prioridade_label(t['prioridade'])}) atribuída ao Servidor {sid} "
                    f"[{policy.upper()}]"
                )

            # Atualiza o último servidor que executou a tarefa
            t["last_worker"] = sid

            # Atualiza lista de servidores livres depois da atribuição
            livres = [sid for sid, st in estados.items() if st["load"] < st["cap"]]

        # ============================
        # PROCESSAR RESPOSTAS DOS WORKERS
        # ============================
        while True:
            resp = receber_resposta(retorno, block=False)
            if not resp:
                break

            sid = resp["worker"]
            estados[sid]["busy"] += resp["duration"]
            estados[sid]["load"] -= 1

            now2 = time.time()
            elapsed2 = now2 - start

            # Atualiza a tarefa correspondente na lista pending
            for p in pending:
                if p["id"] == resp["id"]:
                    p["remaining"] = resp["remaining"]
                    p["running"] = False
                    break

            if resp["remaining"] == 0:
                completed[resp["id"]]["end"] = now2
                pending = [p for p in pending if p["id"] != resp["id"]]
                print(
                    f"{ts(elapsed2)} Servidor {sid} concluiu Requisição {resp['id']} "
                    f"| CPU {resp['cpu']:.1f}% | RAM {resp['memory']:.1f}MB"
                )
            else:
                print(
                    f"{ts(elapsed2)} Servidor {sid} preemptou Requisição {resp['id']} "
                    f"(restante {resp['remaining']:.1f}s) "
                    f"| CPU {resp['cpu']:.1f}% | RAM {resp['memory']:.1f}MB"
                )

        # Condição de parada: todas as tarefas concluídas
        if all(t["remaining"] == 0 for t in pending):
            break

        time.sleep(0.05)

    # ============================
    # MÉTRICAS FINAIS
    # ============================
    total = time.time() - start

    tempos = [(c["end"] - c["arrival"]) for c in completed.values()]
    avg = sum(tempos) / len(tempos)
    throughput = len(completed) / total
    util = sum((st["busy"] / total) * 100 for st in estados.values()) / len(estados)

    print("-" * 60)
    print(f"Resultados da política: {policy.upper()}")
    print(f"Tempo médio de resposta: {avg:.2f}s")
    print(f"Throughput: {throughput:.2f} tarefas/s")
    for sid, st in estados.items():
        print(f"Servidor {sid} utilização: {(st['busy']/total)*100:.1f}%")
    print("-" * 60)

    # Encerra workers
    for q in filas.values():
        q.put("EXIT")

    return {"tempo_medio": avg, "throughput": throughput, "utilizacao": util}


def main():
    cfg = carregar_config()

    politicas = {
        "RR": "rr",
        "SJF": "sjf",
        "PRIORIDADE": "prioridade"
    }

    resultados = {
        nome: executar_politica(pol, cfg)
        for nome, pol in politicas.items()
    }

    print("\n" + "=" * 60)
    print("                  RESUMO FINAL")
    print("=" * 60)
    print("+-------------+--------------+-------------+------------+")
    print("| Algoritmo   | Tempo Médio  | Throughput  | Utilização |")
    print("+-------------+--------------+-------------+------------+")

    for nome, r in resultados.items():
        print(
            "| {:11} | {:12} | {:11} | {:10.1f}% |".format(
                nome,
                f"{r['tempo_medio']:.2f}s",
                f"{r['throughput']:.2f}/s",
                r["utilizacao"],
            )
        )

    print("+-------------+--------------+-------------+------------+")

    print("\nResumo Geral:")
    print(
        f"Tempo médio geral: "
        f"{sum(r['tempo_medio'] for r in resultados.values())/3:.2f}s"
    )
    print(
        f"Throughput médio: "
        f"{sum(r['throughput'] for r in resultados.values())/3:.2f} tarefas/s"
    )
    print(
        f"Utilização média da CPU simulada: "
        f"{sum(r['utilizacao'] for r in resultados.values())/3:.1f}%"
    )
    print("-" * 60)
    print("TODAS AS POLÍTICAS FORAM SIMULADAS.")


if __name__ == "__main__":
    main()
