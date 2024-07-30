from openai import OpenAI

import os

OPENAI_CLIENT = OpenAI()

class NaiveGenerator:
  def __init__(self):
    self._validate_env_variables()
    
    # System prompt is like the pre-set instruction given to the model.
    # It molds/steers the behavior of the model.
    # Example of system prompt: You are a Blockchain Development Tutor. Your mission is to guide users from zero knowledge to understanding the fundamentals of blockchain technology and building basic blockchain projects. Start by explaining the core concepts and principles of blockchain, and then help users apply that knowledge to develop simple applications or smart contracts. Be patient, clear, and thorough in your explanations, and adapt to the user's knowledge and pace of learning.
    # https://github.com/mustvlad/ChatGPT-System-Prompts
    self._system_prompt = f"""
      You are an artificial intelligence (AI) researcher. Your goal is to understand the fundamentals of AI and help the user understand AI concepts ranging from the basics to advance theories. When answering the user, you can provide the technical answers but focus more on the real life implications and applications.  
      """
      
  def _validate_env_variables(self):
    if not os.getenv('OPENAI_API_KEY'):
        raise EnvironmentError("Environment variable 'OPENAI_API_KEY' not set. Please ensure it is defined in your .env file.")

  def _generation_prompt(self, question, context): 
    # TODO: fill in the prompt
    return f"""
      I am an AI developer trying to learn about AI and build an AI application. I will provide you with my question and then some context for you to answer my question. You can use the context provided when appropriate. If the context is not relevant to the question or does not help answer the question, please indicate so in your response. If you cannot answer the question or do not have enough information to answer the question, please indicate so in your response.

      Question: {question}
      
      Context: {context}
      """

  def get_completion(self, question, context):
    completion_obj = OPENAI_CLIENT.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=[
        {
          "role": "system",
          "content": f"{self._system_prompt}"
        },
        {
          "role": "user",
          "content": f"{self._generation_prompt(question, context)}"
        }
      ],
      temperature=0,
      max_tokens=256,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0
    )
    return completion_obj.choices[0].message.content