from langchain.prompts import PromptTemplate

output_format_template = PromptTemplate(
    input_variables=["pentest_plan", "pentest_scope", "suggested_tools"],
    template = '''
    ###
    {pentest plan}
    ###
    {pentest scope}
    ###
    {suggested tools}
    ###
    '''
)

investigation_format_template = PromptTemplate(
    input_variables=["investigation_plan", "investigation_scope", "suggested_files"],
    template = '''
    ###
    {investigation plan}
    ###
    {investigation scope}
    ###
    {suggested files}
    ###
    '''
)

objective_templates = {
    "scope": PromptTemplate(
    input_variables=["files"],
    template=
    '''
    Of the program files provided determine the scope, this includes the files and list of their dependencies:
    {files}
    '''),
    "tooling": PromptTemplate(
    input_variables=["pentest_plan"],
    template=
    '''
    Provide a list of the suggested tools a penetration tester would use to perform a penetration test based on your plan:
    {pentest_plan}
    '''),
    "plan": PromptTemplate(
    input_variables=["api_environment"],
    template=
    '''
    Provide a plan for performing a penetration test. This is a step-by-step process which includes the methods and vulnerable functions,
    methods, or configurations which will be exploited to attack the API environment:
    {api_environment}
    ''')
}

investigation_templates = {
    "files": PromptTemplate(
    input_variables=["files"],
    template=
    '''
    Of the logs files provided determine the scope, this includes the files and their relevance:
    {files}
    '''),
    "plan": PromptTemplate(
    input_variables=["investigation_plan"],
    template=
    '''
    Provide a logical path of attack for perfmoring an cyber-incident response investigation based on the evidence:
    {investigation_plan}
    '''),
    "environment": PromptTemplate(
    input_variables=["environment"],
    template=
    '''
    Provide a reasons for indicators of compromise. This is a step-by-step process which includes the methods and indicators of compromise,
    methods, or configurations which were exploited to attack the environment:
    {api_enviroment}
    ''')
}

system_prompt = PromptTemplate(
    template=
    '''
    You are an expert penetration tester for API Security specializing in white-box testing. Generate a pentest report that includes:
    1. A pentest plan for performing the penetration test.
    2. The scope of the penetration test based on provided files.
    3. Suggestions for the tools to be used for the test.
    '''
)

investigation_prompt = PromptTemplate(
    input_variables=["data"],
    template=
    '''
    You are an expert investigative analyst for a security operations center. Your role is to conduct a thorough investigation on 
    cyber-incidents by indentifying indicators of compromise by examining data. You work alongside human investigators. If indicators
    of compromise are not clear you provide direction and reasons for a human to analyze.
    {data}
    '''
)

summary_prompt = PromptTemplate(
    input_variables=["context"],
    template=
    '''
    You are an expert investigative analyst for a security operations center. Your role is to preliminary investigation on 
    cyber-incidents by summary documents supplied and suggesting potentianl indicators of compromise by examining data. 
    Your output will be read byhuman investigators. If indicators of compromise are not clear provide direction and reasons 
    for a human to continue the analysis.
    {context}
    '''
)

Doc_Analysis_prompt = PromptTemplate(
    input_variables=["context"],
    template=
    '''
    You are an expert investigative analyst for a security operations center. Your role is to investigate 
    cyber-incidents by summarizing documents supplied and suggesting potential indicators of compromise by examining data. 
    Your output will be read by human investigators. If indicators of compromise are not clear provide direction and reasons 
    for a human to continue the analysis. 
    {context}
    '''
)

Q_A_prompt = PromptTemplate(
    input_variables=["document_context","scan_context", "history"],
    template=
    '''
    The context is past conversations, tool scan results, and documents supplied. 
    You are to respond to the user query based on the context provided.
    
    ####Document Context###
    {document_context}

    ####scan results###
    {scan_context}

    ###Chat History###
    {history}
    '''
)

Asset_Disc_Prompt = PromptTemplate(
    input_variables=["asset_data"],
    template=
    '''
    Generate a report detailing the status of the asset for reporting and remediation purposes.
    Format it to be an email.

    Always recommend for offline or stale agents the need to properly update or maintain an online status to reduce
    blindspots in the monitoring software.
    {asset_data}
    '''
)

LCEL_Query_Prompt = PromptTemplate(
    input_variables=["context"],
    template=
    '''
    Generate an LCEL query based on the provided context.
    {context}
    '''
)
