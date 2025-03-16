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

## How to Use

### 1. Configure OpenAI API Key and OpenAI Assistant (Agent)

Get an OpenAI API key and set it as an environment variable.

```
OPENAI_API_KEY="your_api_key_here"
```
Create and set the configuration of your agents in a JSON file `config/assistants.json`. You can refer to [config/assistants_sample.json](https://github.com/orvinbellamy/stock_rag/blob/main/config/assistants_sample.json) as an example. You can create assistants OpenAI itself and get the assistant_id, or create it using `AgentHandler`.

    
    with open('config/assistants.json', 'r') as json_file:
	    dic_assistants = json.load(json_file)
    
    ag_ceo = AgentHandler(
	    client=client,
	    new=True, # Make sure this is set to True if you're creating a new assistant
	    assistant_name='name',
	    dic_file=dic_assistants
	)
Unfortunately assistant_id used in to create the script cannot be shared. 

### 2. Set up the Finance Data from Yahoo Finance (Optional)
The demo in the Jupyter Notebook [main.ipynb](https://github.com/orvinbellamy/stock_rag/blob/main/main.ipynb) simulates a stock analysis uses Yahoo Finance data, but the remaining code can be used for other context.

```
## Configuration
FILE_PATH = 'openai_upload_files/'
OPENAI_DIC_FILE_NAME = 'openai_files.json'

# Load schemas from JSON file
with  open('config/dataframe_schemas.json', 'r') as f:
	schemas = json.load(f)

# Open dic_files
with  open(f'{FILE_PATH}{OPENAI_DIC_FILE_NAME}', 'r') as f:
	dic_files = json.load(f)

with  open('config/assistants.json', 'r') as json_file:
	dic_assistants = json.load(json_file)

ticker = ['MSFT']

stock_data_config = {
	'price': {'period': '5y'},
	'cashflow': {'period': 'quarter'},
	'income_statement': {'period': 'quarter'},
	'balance_sheet': {'period': 'quarter'}
}

dic_file_manager = stock_data_setup(
	client=client, 
	ticker=ticker, 
	config=stock_data_config,
	dic_files=dic_files)
```
### 3. Set the Agents
```
agent_thread_manager = AgentThreadManager()

ag_ceo = AgentHandler(
	client=client,
	new=False, # Can be set to True for new assistant (agent)
	assistant_name='Name',
	dic_file=dic_assistants
)

# If the agent needs to be given data
ag_stock_price_analyst.update_agent(
	agent_files=[dic_file_manager['file_name'].file_id]
)
```
### 4. Set the Nodes
One node can contain multiple agents, but there must be one main agent.
```
nd_main_node = SystemNode(
	client=client,
	name='node_name',
	main_agent=ag_main_agent,
	sub_agents=[ag_sub_agent_1, ag_sub_agent_2, ag_sub_agent_3],
	agent_thread_manager=agent_thread_manager
)
```
### 5. Set the Controller (`MultiNodeManager`)
```
multi_nodes_schema = {
	nd_main_node: set([nd_node_1, nd_node_2, nd_node_3]),
	nd_node_1: set(),
	nd_node_2: set(),
	nd_node_3: set()
}

nodes_manager = MultiNodeManager(schema=multi_nodes_schema, schema_depth=2)
```
### 6. Give your Prompt to the Controller
```
prompt  =  """
	This is a message from Client:
	I want your assessment on the stock ticker 'MSFT'
"""
output  =  nodes_manager.run(prompt=prompt)
print(output)
```