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
MODEL = 'gpt-3.5-turbo'


def chat(system_prompt, session_id, message):
    system_prompt = system_prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content=system_prompt
            ),
            MessagesPlaceholder(
                variable_name="chat_history"
            ),
            HumanMessagePromptTemplate.from_template(
                "{human_input}"
            ),
        ]
    )

    message_history = RedisChatMessageHistory(
        url=REDIS_URL, session_id=session_id)
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
