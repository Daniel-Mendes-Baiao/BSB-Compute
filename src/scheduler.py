class Scheduler:

    def __init__(self, policy="prioridade"):
        self.policy = policy

    def reorder(self, fila):
        if not fila:
            return

        if self.policy == "sjf":
            fila.sort(key=lambda t: t["remaining"])
        elif self.policy == "prioridade":
            fila.sort(key=lambda t: t["prioridade"])

    def next_task(self, fila):
        return fila.pop(0)
