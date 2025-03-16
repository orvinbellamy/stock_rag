# Multi AI Agent System (stock_rag)

Project link: https://github.com/orvinbellamy/stock_rag
Contributor: Orvin Bellamy (https://github.com/orvinbellamy)
Last update: 14th March 2025
Python 3.9.13

## About The Project

The goal of this project is to manage and facilitate communications between multiple LLM agents. Although there are frameworks that does this more efficiently, this is project serves as a simpler demonstration on how to utilize multiple LLM agents. This project uses OpenAI's GPT model, although the designs and concepts used can be replicated with other models.

The example used in this project is creating an organization consisting of multiple agents (GPT models) roleplaying as a finance team tasked with analyzing a stock. Each agent will have their own role and work in a hierarchy where an agent can have superiors and subordinates. Data from Yahoo Finance is used for the simulation, although the agents and data can be modified to the user's requirements.
## Requirements

 - See requirement.txt for all Python libraries used
 - OpenAI API key

## Design

Although the concept can be applied to other LLM models, the code in this project is built based on OpenAI's API, hence some design decisions are built for OpenAI's API in mind.

Here are the entities that makes up the multi agent system:

 - Agent: the LLM model
 - Thread: stores messages between user and agent(s)
 - Node: facilitates communications between multiple agents in a single thread
 - Controller (`MultiNodeManager`): facilitates communications between multiple nodes

Relationship between agent, thread, node, and controller
![diagram-1.jpg](https://i.postimg.cc/PrSxTcTz/diagram-1.jpg)

### Node
A node contains one main agent, sub agent(s), and one thread. All agents are assigned to the thread (see `AgentThreadManager`). A node takes an input (prompt), gives it to the main agent, and the main agent will give instructions (prompt) for all the sub agents. The node then gives the input to the sub agents, and then takes the outputs of the sub agents and gives it to the main agent. Depending on the output, the main agent may choose to provide more instructions to the sub agent or summarizes the output and end the cycle.
![node.jpg](https://i.postimg.cc/zXfLbWDr/node.jpg)

### Sample of a Full Run

![run.jpg](https://i.postimg.cc/3xcb5gNJ/run.jpg)
