A Health&Med, é uma Operadora de Saúde que tem como objetivo digitalizar
seus processos e operação. O principal gargalo da empresa é o Agendamento
de Consultas Médicas, que atualmente ocorre exclusivamente através de
ligações para a central de atendimento da empresa.
Recentemente, a empresa recebeu um aporte e decidiu investir no
desenvolvimento de um sistema proprietário, visando proporcionar um
processo de Agendamentos de Consultas Médicas 100% digital e mais ágil.
Para viabilizar o desenvolvimento de um sistema que esteja em conformidade
com as melhores práticas de desenvolvimento, a Health&Med contratou os
alunos da turma SOAT da Pós Graduação da FIAP para fazer a análise do
projeto e desenvolver o MVP da solução.
O objetivo do Hackathon é a entrega de um produto de MVP desenvolvido e
que cumpra os requisitos funcionais e não funcionais descritos abaixo.
Considerações importantes:
*Não haverá a necessidade do desenvolvimento de Frontend
*Os times do Hackathon terão autonomia para tomar as decisões de
arquitetura e decidir como será feito o desenvolvimento, aplicando os
conhecimentos adquiridos durante o curso de Pós Graduação SOAT.

1. [x] Cadastro do Usuário (Médico)
       O médico deverá poder se cadastrar, preenchendo os campos
       obrigatórios: Nome, CPF, Número CRM, E-mail e Senha.
2. [x] Autenticação do Usuário (Médico)
       O sistema deve permitir que o médico faça login usando o E-mail e uma
       Senha.
3. [x] Cadastro/Edição de Horários Disponíveis (Médico)
       O sistema deve permitir que o médico faça o Cadastro, Edição de seus
       dias e horários disponíveis para agendamento de consultas.
4. [x] Cadastro do Usuário (Paciente)
       O paciente poderá se cadastrar preenchendo os campos: Nome, CPF,
       E-mail e Senha.
5. [x] Autenticação do Usuário (Paciente)
       O sistema deve permitir que o paciente faça login usando o E-mail e
       Senha.
6. [x] Busca por Médicos (Paciente)
       O sistema deve permitir que o paciente visualize a listagem dos
       médicos disponíveis.
7. [x] Agendamento de Consultas (Paciente)
       Após selecionar o médico, o paciente deve visualizar os dias e horários
       disponíveis do médico.
       O paciente poderá selecionar o horário de preferência e realizar o
       agendamento.
8. Notificação de consulta marcada (Médico)
   Após o agendamento, feito pelo usuário Paciente, o médico deverá
   receber um e-mail contendo:
   Título do e-mail:
   ”Health&Med - Nova consulta agendada”
   Corpo do e-mail:
   ”Olá, Dr. {nome_do_médico}!
   Você tem uma nova consulta marcada!
   Paciente: {nome_do_paciente}.
   Data e horário: {data} às {horário_agendado}.”
   Hackathon 3
   Requisitos Não Funcionais
9. [x] Concorrência de Agendamentos
       O sistema deve ser capaz de suportar múltiplos acessos simultâneos e
       garantir que apenas uma marcação de consulta seja permitida para um
       determinado horário.
10. [x] Validação de Conflito de Horários
        O sistema deve validar a disponibilidade do horário selecionado em
        tempo real, assegurando que não haja sobreposição de horários para
        consultas agendadas.

## Entregáveis Mínimos

    Os grupos deverão entregar o seguinte:

11. [x] Desenvolvimento de um MVP da solução, contemplando os requisitos
        funcionais e não funcionais listados acima.
12. Pipeline CI/CD
    a. Demonstração do pipeline de deploy da aplicação.
13. Testes unitários
    a. Implantação de testes unitários que garantam o funcionamento da
    solução
14. [x] Não há a necessidade do desenvolvimento do Frontend da Solução.
15. Formato da entregável: Vídeo gravado que demonstre o funcionamento do
    sistema cumprindo os requisitos solicitados e Documentação escrita
    (README ou Arquivo)
    a. A duração máxima do vídeo deverá ser de, no máximo, 10 minutos.
    Vídeos mais longos não serão corrigidos.
