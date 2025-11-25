The required Python version is 3.11.9

To setup:
1) brew install pyenv (Mac/Linux)
2) pyenv install 3.11.9
3) pyenv global 3.11.9
4) Check using: python --version
5) cd /path/to/your/project
6) python3.11 -m venv <project name>
7) Activate your environment: source <project name>/bin/activate
8) upgrade pip: pip install --upgrade pip
9) Install packages: pip install -r requirements.txt
10) Install Ollama for your OS (https://ollama.com/).
11) Download the mistral 7b model using 'ollama run mistral'
12) Start the program using "python dash_ui_ReAct.py"

**Project Description** TThis project demonstrates an LLM-based agentic system that operates entirely within a local environment to ensure data privacy and security. By leveraging locally runnable, open-source Large Language Models (LLMs), this tool supports SOC analysts in automating everyday tasks without sending sensitive infrastructure data to third-party cloud providers.

The system utilizes Mistral 7B and the LangChain ReAct (Reasoning + Acting) framework to enable autonomous agents. These agents can intelligently interpret natural language queries, select the appropriate tools, and execute tasks such as asset reporting and SIEM query generation. 

**Note** The setup step is going to require a variable amount of debugging, dependent on your environment. We've done our best to minimize this. 

**Hardware Used** We ran this program and local models on a MacBook Pro M2 with 32 GB of RAM. 

**File Descriptions**

The project currently uses the Dash UI, and the frontend for the project can be found in the *dash_ui_ReAct.py* file.

The */fusion_assistant_ReAct* directory is the core of the project. 

*app.py* is the driver for the backend of the system. 

*react_agent.py* is what defines and implements the use of the LangChain ReAct chain feature for autonomous agent calling.

*/fusion_assistant_ReAct/agents* is where agents are defined and implemented. There are two agents *asset_agent.py* for asset discovery and *lcel_agent.py* for generating LEQL queries on request.

Both agents are supplied with their own vector stores for document retrieval; the vector store and retriever code can be located at */fusion_assistant_ReAct/retrieval*.

The project provides logging to enable auditing and analysis of input/output pairs. The LLM agents are also designed to include a memory system using the LangChain conversational buffer. This code is in the *fusion_assistant_ReAct/persistence* directory.

Files for model and prompt modifications can be found in the *fusion_assistant_ReAct/llm* directory. However, model usage is strictly defined in *fusion_assistant_ReAct/config/model_config.yaml* file.

Helper functions for performing IO and data ingestion are located in the *fusion_assistant_ReAct/io* directory. You will also find all of the path assignments, which can be modified in the paths.py file.

*/query_examples* is used as the examples for generating LQEL queries; most of these examples were scraped from the https://docs.rapid7.com/insightidr/example-queries/ website. We've also included 
an additional example (Excessive_Failed_Login.txt) from my experience working in an industry SOC.

*/assets_test* is a directory which contains examples of what assets may exist on a corporate network for which the asset discovery uses to report on using the email template located in the 
/email_reporting directory.

The query_DS Excel file includes examples of queries and the expected outcomes when the tool is used. It also provides the expected tool for the LangChain React chain implementation.
