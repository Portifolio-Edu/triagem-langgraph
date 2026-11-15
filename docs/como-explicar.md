# Como explicar este projeto em entrevista

**Em uma frase:** é a triagem de atendimento que eu fiz em n8n para um escritório de contabilidade, reescrita em Python com LangGraph, com as duas falhas que aconteceram em produção resolvidas por desenho e provadas por teste.

## O que é o estado
Um `TypedDict` (`Estado`) com tudo o que a mensagem acumula no caminho: texto, classificação, decisão, protocolo, evento, resposta e o caminho percorrido. Cada nó lê o estado e devolve só o que mudou. Cada mensagem entra com o estado zerado, para nada da volta anterior vazar. A conversa é o `thread_id` do checkpointer.

## Por que arestas condicionais
Porque o caminho depende do dado: mensagem vazia não precisa de classificação, pedido repetido não precisa de pessoa, confiança baixa precisa. A decisão fica numa função pequena (`depois_de_registra`) que dá para ler e testar, e não escondida dentro de um prompt.

## Por que o modelo só classifica
Setor, prazo e "vai para pessoa" são regra de negócio. Regra em Python dá o mesmo resultado toda vez e cabe em teste. O modelo entra onde ele é bom: entender o texto livre do cliente e devolver uma saída estruturada.

## Por que o guardrail fica fora do prompt
Em produção o agente disse que um pedido "estava em análise" e prometeu retorno sem ter essa informação. Instrução no prompt diminui a chance, não garante. O validador roda depois do modelo, corta a frase inteira e registra o motivo. Se sobrar nada, a resposta mínima é sempre verdadeira: o protocolo.

## Por que pedido novo vai para a frente
O outro erro de produção: pedido novo caía dentro de uma demanda antiga e sumia. Agora ele vai para a frente do resumo, o anterior fica atrás, gera evento próprio, e a chave de idempotência impede que a mesma mensagem reenviada vire duplicata.

## Por que interrupção
Quando precisa de pessoa, o grafo para no nó `humano`, grava o estado no SQLite e volta com `Command(resume=...)`. O teste prova que retoma até depois de reiniciar o processo.

## Por que teste sem modelo
Custo zero e resultado igual toda vez. O `ModeloFalso` é determinístico e o replay usa rascunhos gravados (o texto que um modelo escreveu) para provar o guardrail. Foi o mesmo método que usei em produção para validar a correção antes de liberar.

## O que eu faria diferente em escala
- Postgres no lugar do SQLite, para demandas e para o checkpointer.
- Modelo real atrás da mesma interface, com avaliação por bateria de casos antes de trocar de modelo ou de prompt.
- Feriados e expediente por cliente na conta de horas úteis.
- Fila para mensagens que chegam enquanto a conversa espera uma pessoa.
- Métricas por nó: quantas vão para pessoa, quantos cortes do guardrail, tempo até o protocolo.
