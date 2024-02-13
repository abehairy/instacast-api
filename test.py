import redis
import ai_host
from db import podcasts

podcast = next(
    (podcast for podcast in podcasts if podcast['id'] == 'innerview'), None)
text = podcast['systemPrompt']
print(text)


# # Connect to Redis
# r = redis.Redis(host='localhost', port=6379, db=0)

# Set a key
response = ai_host.chat(
    text, '32f9897c-9cfc-4c8d-ab4b-a714334f1350', 'love my work')

print(response)
