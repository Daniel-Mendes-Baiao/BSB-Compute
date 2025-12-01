def enviar_tarefa(queue, tarefa):
    queue.put(tarefa)

def receber_resposta(queue, block=True, timeout=None):
    try:
        if block:
            return queue.get(timeout=timeout)
        else:
            return queue.get_nowait()
    except Exception:
        return None
