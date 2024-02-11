from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain.schema import SystemMessage
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory, RedisChatMessageHistory
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

REDIS_URL = 'redis://localhost:6379'
# REDIS_URL = 'redis://:pe34bde2193e50875b9f66dc43ac62b1b739394c40728134c0e81066ecaf20e31@ec2-3-229-82-17.compute-1.amazonaws.com:20119'
MODEL = 'gpt-3.5-turbo'
# MODEL = 'gpt-4-0613'


def chat(message):
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content=""""
             You are the host for the podcast 'Innerview', where you help discover the guest journey and let people from different walks of lives tell their stories. 
             Start by introducing the show and then go ahead and ask the user about their journey
             then let the conversation flow as if you're a joe rogan.

             Make sure to only introduce the prodcast if there's no chat history and it's the first time. If not pick up where 
             the conversation stopped.

                """
            ),  # The persistent system prompt
            MessagesPlaceholder(
                variable_name="chat_history"
            ),  # Where the memory will be stored.
            HumanMessagePromptTemplate.from_template(
                "{human_input}"
            ),  # Where the human input will injected
        ]
    )

    message_history = RedisChatMessageHistory(
        url=REDIS_URL, session_id='behairy')
    memory = ConversationBufferMemory(
        memory_key="chat_history", memory=ConversationBufferMemory(
            input_key="human_input", chat_memory=message_history), return_messages=True)
    llm = ChatOpenAI()

    chat_llm_chain = LLMChain(
        llm=llm,
        prompt=prompt,
        verbose=True,
        memory=memory,
    )

    return chat_llm_chain.predict(human_input=message)
