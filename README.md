 InovaFarma Smart Updater
Este programa foi criado para automatizar a atualização do sistema InovaFarma. O objetivo é simples: eliminar o trabalho manual de passar em cada computador da farmácia para atualizar o ERP, reduzindo drasticamente os chamados de suporte.

 Como usar (Passo a passo)
Para configurar, você só precisa fazer isso uma vez em cada terminal:

1.Coloque o executável do atualizador dentro da pasta onde o InovaFarma está instalado.
2.Clique com o botão direito no atualizador, vá em Propriedades > Compatibilidade e marque a caixa "Executar este programa como administrador".
3.Abra o programa manualmente apenas uma vez.

Por que? Ao abrir a primeira vez, ele mesmo cria uma tarefa no Windows para iniciar sozinho e com permissão total sempre que o computador for ligado. Não precisa criar atalhos na pasta de inicialização.

O que usei para construir (Stack Técnica)
Se você quer entender a lógica por trás da ferramenta, aqui estão os destaques:

Python: A base de toda a automação e lógica de busca.

PyQt6: Utilizado para criar a interface de acompanhamento do usuário.

GraphQL: Usei para conversar com a API oficial e buscar apenas os links de versões estáveis.

Multi-threading: O download e a instalação rodam em uma linha separada (Thread) para a janela não "congelar" enquanto trabalha.

Windows Registry & Winreg: O script lê o registro do Windows para saber qual versão você já tem instalada antes de decidir se precisa baixar algo.

PowerShell Bridge: Criei um script que roda em segundo plano para "consertar" o atalho da barra de tarefas. Quando o executável do InovaFarma muda, o Windows costuma quebrar o atalho fixado; essa ponte resolve isso automaticamente.