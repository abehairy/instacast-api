from db import podcasts

podcast = next(
    (podcast for podcast in podcasts if podcast['id'] == 'innerview'), None)
text = podcast['introPrompt']
print(text)
