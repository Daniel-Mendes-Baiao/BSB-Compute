# BSB Compute – Simulador de Escalonamento em Cluster

Este projeto implementa um simulador de algoritmos de escalonamento em um cluster de servidores, usando **multiprocessing**, **psutil**, e um sistema completo de **scheduler + workers + IPC**.

A execução simula três políticas de escalonamento:

- **RR (Round Robin)**
- **SJF (Shortest Job First)**
- **PRIORIDADE**

No final da simulação, uma **tabela comparativa** e um **resumo geral** são exibidos no terminal, consolidando as principais métricas de desempenho de cada algoritmo.

---

## 🚀 Objetivo do Projeto

O trabalho simula o funcionamento de um cluster processando requisições, avaliando:

- comportamento das políticas de escalonamento  
- tempo médio de resposta  
- throughput  
- utilização dos servidores  
- impacto da carga no sistema  

A simulação busca aproximar o comportamento de um sistema real, seguindo fielmente o modelo solicitado no PDF do projeto.

---

## 🏛 Arquitetura do Sistema

### 🔹 **1. Orquestrador (`main.py`)**
- Carrega o config.json  
- Executa cada algoritmo separadamente  
- Cria filas de comunicação e inicia os processos  
- Encaminha requisições para os servidores  
- Recebe respostas dos workers  
- Gera logs e consolida métricas  
- Mostra **uma única tabela final** e um **resumo geral**

### 🔹 **2. Scheduler (`scheduler.py`)**
Implementa as três políticas:

- **RR** → fatia de tempo (quantum)
- **SJF** → menor tempo restante
- **PRIORIDADE** → prioridade numérica

### 🔹 **3. Worker (`worker.py`)**
Cada worker simula:

- execução de fatias (RR) ou job completo  
- tempo de processamento proporcional ao workload  
- coleta *simulada* de CPU e RAM com psutil  
- retorno ao orquestrador via fila multiprocessing  

### 🔹 **4. IPC (`ipc.py`)**
Canais simples de troca de mensagens via multiprocessing.Queue.

### 🔹 **5. Utils (`utils.py`)**
Funções auxiliares para timestamps e salvar relatórios.

---

## ⚙️ Arquivo de Configuração (`config.json`)

Todas as requisições e servidores estão configurados aqui:

```json
{
    "servidores": [
        {"id": 1, "capacidade": 3},
        {"id": 2, "capacidade": 2},
        {"id": 3, "capacidade": 1}
    ],
    "quantum": 1,
    "requisicoes": [
        {"id": 101, "tipo": "visao_computacional", "prioridade": 1, "tempo_exec": 4},
        {"id": 102, "tipo": "nlp", "prioridade": 3, "tempo_exec": 3},
        {"id": 103, "tipo": "voz", "prioridade": 2, "tempo_exec": 5}
    ]
}
```

## ▶️ Como Executar

No terminal:

```bash
python src/main.py
```

A saída exibirá:

1. logs da simulação RR  
2. logs da simulação SJF  
3. logs da simulação Prioridade  
4. **uma tabela final única** com todas as métricas  
5. **um resumo geral consolidado**

---

## 🧠 Observações Técnicas

- A simulação usa **multiprocessing de verdade**, criando processos independentes.  
- Workers coletam **CPU e RAM simuladas**, pois o objetivo é imitar um sistema real sem depender da máquina física.  
- RR opera em fatias `quantum`, SJF e Prioridade executam a tarefa inteira.  
- O orquestrador não mede sua própria CPU – apenas os workers, como requerido.  

---