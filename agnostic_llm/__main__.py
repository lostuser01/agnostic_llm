"""python -m agnostic_llm [-c config.yaml] [-m route_or_model] "your prompt"  (no prompt = chat)"""
import argparse
from . import Message, Models

p = argparse.ArgumentParser()
p.add_argument("prompt", nargs="*")
p.add_argument("-c", "--config", default="config.yaml")
p.add_argument("-m", "--model", default="default")
a = p.parse_args()

llm = Models.from_file(a.config).get(a.model)
if a.prompt:
    print(llm.ask(" ".join(a.prompt)))
else:
    hist = []
    print(f"Chatting with {llm.name}. Ctrl-C to quit.")
    while True:
        hist.append(Message("user", input("you> ")))
        r = llm.chat(hist)
        hist.append(Message("assistant", r.text))
        print(f"ai> {r.text}\n")
