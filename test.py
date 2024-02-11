from dotenv import load_dotenv
import asyncio
import sys
import json
import sys
from pathlib import Path


async def chat(user_input):

    from base_agent.agent import BaseAgentExecutor
    agent = BaseAgentExecutor()
    response = await agent.chat(user_input)

    return response


if __name__ == '__main__':

    from base_agent.data_retrieval_tools import query_user_data
    p = query_user_data(
        'what are the exact detailed process for registering a product in egypt')
    print(p)

    # response = asyncio.run(chat(sys.argv[1]))
