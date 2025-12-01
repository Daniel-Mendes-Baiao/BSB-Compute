import time
import psutil
from multiprocessing import Process
from queue import Empty


def simular_metricas(work):
    cpu = min(100, work * 15)     # Simulação simples
    ram = 20 + (work * 2.0)
    return cpu, ram


def worker_loop(worker_id, fila_entrada, fila_retorno):
    proc = psutil.Process()

    while True:
        try:
            msg = fila_entrada.get(timeout=0.2)
        except Empty:
            continue

        if not isinstance(msg, dict):
            break
        if msg.get("EXIT", False) or msg == "EXIT":
            break

        if "slice" in msg:
            work = float(msg["slice"])
            time.sleep(work)
            remaining = msg["remaining"] - work
        else:
            work = float(msg["exec_time"])
            time.sleep(work)
            remaining = 0.0

        cpu_sim, ram_sim = simular_metricas(work)

        fila_retorno.put({
            "id": msg["id"],
            "worker": worker_id,
            "duration": work,
            "remaining": max(0.0, remaining),
            "cpu": cpu_sim,
            "memory": ram_sim
        })


def iniciar_workers(cfg, filas, retorno):
    procs = []
    for s in cfg:
        sid = s["id"]
        p = Process(target=worker_loop, args=(sid, filas[sid], retorno))
        p.start()
        procs.append(p)
    return procs
