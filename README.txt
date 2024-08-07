README

TODO:
- Replies from assistant are in different chunks inside the thread. Need to combine them
- Replies from assistant can include attachments (no text), need to accommodate this.
	- messages[0].content[i].type = 'image_file' or 'text
- Test to see if __init__ of AgentHandler is working properly
- Test to see if 2 agents can work in 1 thread