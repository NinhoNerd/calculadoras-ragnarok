# Calculadora Ragnarok Online LATAM (Excel)

## Descrição
Este projeto reúne uma planilha Excel (`Calculadora.xlsx`) para calcular resultados baseados em atributos diferentes regras de criação de itens e opções para futura distribuição como aplicativo (executável) simples.

---

## Objetivo
1. Centralizar o cálculo dos valores **mínimos**, **máximos** da fórmula de Farmacologia Avançada, e derivar a quantidade de poções criadas a partir de limiares de diferença entre **A** e **B**.

### Fórmula principal
$$
\text{INT} + \frac{\text{DEX}}{2} + \text{SOR} + \text{CLASSE} + \text{Rand}[30,150] + (\text{BASE} - 100) + (\text{PESQ\_POÇÕES} \times 5) + (\text{PROT\_QUÍMICA} \times \text{Rand}[4,10])
$$


---

## Requisitos
- Excel (Microsoft 365 ou 2019+ recomendado)
- Para uso com fórmulas em inglês: Excel configurado em inglês  
  *(ou manter funções em português se preferir)*
  
---

## Como usar a planilha (Excel)

1. **Preencha os atributos** em suas células indicadas (exemplo em coluna B):
   - `B2` = INT  
   - `B3` = DEX  
   - `B4` = SOR  
   - `B5` = BASE  
   - `B6` = CLASS  
   - `B7` = POTION RESEARCH (Pesquisa de Poções)  
   - `B8` = TOTAL CHEMICAL PROTECTION (Proteção Química Total)

2. **Cálculo de menor, maior e aleatório** — Excel em inglês:
   - Menor possível:
     ```excel
     =B2 + (B3 / 2) + B4 + B6 + 30 + (B5 - 100) + (B7 * 5) + (B8 * 4)
     ```
   - Maior possível:
     ```excel
     =B2 + (B3 / 2) + B4 + B6 + 150 + (B5 - 100) + (B7 * 5) + (B8 * 10)
     ```

3. **Se seu Excel usa `;` como separador**, troque todas as vírgulas por `;`.

