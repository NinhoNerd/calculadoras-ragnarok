# Calculadora Ragnarok 🧪⚗️

Uma calculadora feita em **Python + Qt (PySide6)** para ajudar jogadores de **Ragnarok Online** a planejar a produção de poções, calcular custos, e organizar informações de itens.  
O objetivo é centralizar diversas ferramentas em um único aplicativo de fácil uso, com interface gráfica e atualizações constantes.

---

## ✨ Funcionalidades

- **Farmacologia Avançada**  
  - Cálculo da chance de sucesso na produção de poções.  
  - Rendimento médio por uso da habilidade.  

- **Catálogo de Itens**  
  - Visualização de materiais e itens finais.  
  - Ícones e nomes em português incluídos.  
  - Receitas vinculadas a cada item.  

- **Custos & Preços** *(em desenvolvimento)*  
  - Cálculo do custo de produção por poção.  
  - Comparação entre diferentes métodos de produção.  

- **Arquivos de Configuração em JSON**  
  - Itens, preços, regras de farmacologia e estatísticas armazenados em arquivos fáceis de editar.  
  - Possibilidade de expandir e atualizar o catálogo sem alterar o código.  

---

## 🚀 Como usar

1. Baixe a última versão disponível em **[Releases](../../releases)**.  
2. Extraia o arquivo `.zip` em uma pasta de sua preferência.  
3. Execute `CalculadoraRagnarok.exe`.  

> ⚠️ O Windows pode exibir um aviso de “editor desconhecido”. Isso acontece porque o programa ainda não é assinado digitalmente. Basta confirmar para rodar.

---

## 🛠️ Como rodar a partir do código-fonte

Se quiser contribuir ou apenas testar diretamente pelo Python:

```bash
# Clone o repositório
git clone https://github.com/SEU_USUARIO/calculadoras-ragnarok.git
cd calculadoras-ragnarok

# Crie um ambiente virtual e instale as dependências
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt

# Execute o projeto
python -m calc_app

## 📦 Estrutura do Projeto

src/
 └── calc_app/
     ├── core/              # Engine de cálculos e lógica principal
     ├── pages/             # Páginas da interface (Qt Widgets)
     ├── assets/            # Ícones e recursos visuais
     ├── __main__.py        # Ponto de entrada da aplicação
     └── config.py          # Configurações gerais


## 🤝 Contribuindo
Este projeto está em estágio inicial (alpha), e toda ajuda é bem-vinda!
- Abra uma issue para sugerir melhorias ou reportar bugs.
- Envie pull requests com novas funcionalidades ou correções.

## 📜 Licença
Este projeto é distribuído sob a licença MIT.
Sinta-se livre para usar, modificar e compartilhar.

